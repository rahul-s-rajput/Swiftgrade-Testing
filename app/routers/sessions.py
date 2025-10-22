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


@router.get("/sessions/{session_id}/template")
def get_session_template(session_id: str):
    """Get assessment configuration data for template reuse"""
    try:
        # Get basic session info
        session_res = supabase.table("session").select("*").eq("id", session_id).limit(1).execute()
        if not session_res.data:
            raise HTTPException(status_code=404, detail="Session not found")

        session_data = session_res.data[0]

        # Get questions configuration
        questions_res = supabase.table("question").select("*").eq("session_id", session_id).execute()
        questions = questions_res.data or []

        # Get images with URLs
        images_res = supabase.table("image").select("*").eq("session_id", session_id).order("order_index").execute()
        images = images_res.data or []

        # Get human grades from stats table
        stats_res = supabase.table("stats").select("*").eq("session_id", session_id).limit(1).execute()
        human_grades = {}
        if stats_res.data:
            human_grades = stats_res.data[0].get("human_marks_by_qid", {})

        # Organize images by role
        student_images = [img["url"] for img in images if img["role"] == "student"]
        answer_key_images = [img["url"] for img in images if img["role"] == "answer_key"]
        rubric_images = [img["url"] for img in images if img["role"] == "grading_rubric"]

        # Construct template data
        template_data = {
            "name": session_data.get("name"),
            "model_pairs": session_data.get("model_pairs"),
            "default_tries": session_data.get("default_tries", 1),
            "questions": [{"question_id": q["question_id"], "max_mark": q["max_marks"]} for q in questions],
            "human_grades": human_grades,
            "images": {
                "student_images": student_images,
                "answer_key_images": answer_key_images,
                "rubric_images": rubric_images
            },
            "templates": {
                "rubric": "default",  # Default template since we don't store template names in session
                "assessment": "default"  # Default template since we don't store template names in session
            }
        }

        return template_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session template: {e}")


@router.put("/sessions/{session_id}")
def update_session(session_id: str, payload: dict):
    """Update session properties (e.g., name)"""
    try:
        # Ensure session exists
        res = supabase.table("session").select("id").eq("id", session_id).limit(1).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Session not found")

        # Update only allowed fields
        update_data = {}
        if "name" in payload and payload["name"] is not None:
            update_data["name"] = payload["name"].strip() if payload["name"].strip() else None

        if not update_data:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Perform update
        supabase.table("session").update(update_data).eq("id", session_id).execute()

        return {"message": "Session updated successfully", "updated_fields": list(update_data.keys())}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update session: {e}")


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
