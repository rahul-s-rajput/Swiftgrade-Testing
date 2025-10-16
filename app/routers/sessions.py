from fastapi import APIRouter, status, HTTPException
import uuid

from ..schemas import SessionCreateRes, SessionListItem, SessionCreateReq
from ..supabase_client import supabase

router = APIRouter()


@router.post("/sessions", response_model=SessionCreateRes, status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreateReq | None = None):
    session_id = str(uuid.uuid4())
    try:
        name = (payload.name or "").strip() if payload and payload.name is not None else None
        supabase.table("session").insert({"id": session_id, "status": "created", "name": name}).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {e}")
    return SessionCreateRes(session_id=session_id, status="created")


@router.get("/sessions", response_model=list[SessionListItem])
def list_sessions():
    try:
        res = (
            supabase.table("session")
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        items = res.data or []
        # Ensure shape matches schema (strings for id/status/created_at)
        return [
            SessionListItem(
                id=str(it.get("id")),
                status=str(it.get("status")),
                created_at=str(it.get("created_at")),
                name=(it.get("name") or None),
                selected_models=(it.get("selected_models") or None),
                default_tries=(it.get("default_tries") if it.get("default_tries") is not None else None),
                rubric_models=(it.get("rubric_models") or None),
                assessment_models=(it.get("assessment_models") or None),
                model_pairs=(it.get("model_pairs") or None),  # NEW: Complete model pair specs
            )
            for it in items
            if it.get("id") is not None
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {e}")


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: str):
    try:
        # Ensure it exists (optional)
        res = supabase.table("session").select("id").eq("id", session_id).limit(1).execute()
        if not res.data:
            # Idempotent delete: treat as no-content if already gone
            return
        supabase.table("session").delete().eq("id", session_id).execute()
        return
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {e}")
