import os
from uuid import uuid4
from fastapi import APIRouter, HTTPException, status
from ..schemas import ImageRegisterReq, SignedUrlReq, SignedUrlRes
from ..supabase_client import supabase

router = APIRouter()


def _bad_request(message: str, code: str = "VALIDATION_ERROR", details: dict | None = None):
    ex = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    ex.code = code
    if details:
        ex.details = details
    return ex


@router.post("/images/register")
def register_image(payload: ImageRegisterReq):
    # Basic URL validation (allow http/https/data for local usage)
    if not payload.url or not isinstance(payload.url, str):
        raise _bad_request("url must be a non-empty string")
    if not (payload.url.startswith("http://") or payload.url.startswith("https://") or payload.url.startswith("data:")):
        raise _bad_request("url must start with http(s) or data:")

    # Validate session exists
    s = supabase.table("session").select("id").eq("id", payload.session_id).execute()
    if not s.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_id not found")

    # Idempotency by (session_id, url)
    existing_by_url = (
        supabase.table("image")
        .select("id")
        .eq("session_id", payload.session_id)
        .eq("url", payload.url)
        .execute()
    )
    if existing_by_url.data:
        return {"ok": True}

    # Check slot uniqueness (session, role, order_index)
    existing_slot = (
        supabase.table("image")
        .select("id,url")
        .eq("session_id", payload.session_id)
        .eq("role", payload.role)
        .eq("order_index", payload.order_index)
        .execute()
    )
    if existing_slot.data:
        # Different URL attempting to reuse same slot
        if existing_slot.data[0]["url"] != payload.url:
            raise _bad_request(
                "order_index already used for this role",
                code="ORDER_INDEX_TAKEN",
                details={"role": payload.role, "order_index": payload.order_index},
            )
        return {"ok": True}

    # Enforce contiguous ordering per role starting at 0
    role_recs = (
        supabase.table("image")
        .select("id")
        .eq("session_id", payload.session_id)
        .eq("role", payload.role)
        .execute()
    )
    count_for_role = len(role_recs.data or [])

    if payload.order_index != count_for_role:
        raise _bad_request(
            "order_index must be contiguous per role starting at 0",
            code="NON_CONTIGUOUS_ORDER_INDEX",
            details={"expected": int(count_for_role), "got": payload.order_index, "role": payload.role},
        )

    # Create image record
    try:
        supabase.table("image").insert(
            {
                "session_id": payload.session_id,
                "role": payload.role,
                "url": payload.url,
                "order_index": payload.order_index,
            }
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to register image: {e}")
    return {"ok": True}


def _get_env_bucket() -> str:
    b = os.getenv("SUPABASE_STORAGE_BUCKET", "grading-images")
    if not b:
        raise HTTPException(status_code=500, detail="SUPABASE_STORAGE_BUCKET is not configured")
    return b


def _extract(obj, *keys):
    # Try nested dicts or objects with .data
    if hasattr(obj, "data"):
        obj = getattr(obj, "data")
    if not isinstance(obj, dict):
        return None
    for k in keys:
        if k in obj:
            return obj[k]
    return None


@router.post("/images/signed-url", response_model=SignedUrlRes)
def create_signed_upload_url(payload: SignedUrlReq) -> SignedUrlRes:
    if not payload.filename or "/" in payload.filename or ".." in payload.filename:
        raise _bad_request("invalid filename")
    if not payload.content_type or not isinstance(payload.content_type, str):
        raise _bad_request("content_type is required")

    bucket = _get_env_bucket()

    # Unique path per upload to avoid collisions; organize by random UUID segment
    path = f"{uuid4().hex}/{payload.filename}"

    try:
        resp = supabase.storage.from_(bucket).create_signed_upload_url(path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create signed upload URL: {e}")

    token = _extract(resp, "token")
    signed_url = _extract(resp, "signedUrl", "signed_url", "url")

    # Build a best-effort uploadUrl if SDK doesn't return full URL
    if not signed_url and token:
        base = os.getenv("SUPABASE_URL")
        if not base:
            raise HTTPException(status_code=500, detail="SUPABASE_URL not configured")
        signed_url = f"{base}/storage/v1/object/upload/sign/{bucket}/{path}?token={token}"

    # Prepare headers the client should send
    headers = {
        "Content-Type": payload.content_type,
    }

    # Compute public URL (works if bucket is public); optional otherwise
    try:
        pub_resp = supabase.storage.from_(bucket).get_public_url(path)
        public_url = _extract(pub_resp, "publicUrl", "public_url", "signedUrl", "url")
    except Exception:
        public_url = None

    if not signed_url and not token:
        raise HTTPException(status_code=500, detail="Supabase did not return a signed upload URL or token")

    return SignedUrlRes(
        uploadUrl=signed_url or "",
        token=token,
        path=path,
        headers=headers,
        publicUrl=public_url,
    )
