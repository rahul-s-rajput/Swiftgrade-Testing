from fastapi import APIRouter, status, HTTPException
import uuid

from ..schemas import SessionCreateRes
from ..supabase_client import supabase

router = APIRouter()


@router.post("/sessions", response_model=SessionCreateRes, status_code=status.HTTP_201_CREATED)
def create_session():
    session_id = str(uuid.uuid4())
    try:
        supabase.table("session").insert({"id": session_id, "status": "created"}).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {e}")
    return SessionCreateRes(session_id=session_id, status="created")
