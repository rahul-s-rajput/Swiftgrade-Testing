from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Set, List, Any

from ..schemas import QuestionConfigReq, OkRes, QuestionsRes, QuestionConfigQuestion
from ..supabase_client import supabase


router = APIRouter()


def _bad_request(message: str, code: str = "VALIDATION_ERROR", details: dict | None = None):
    ex = HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)
    ex.code = code
    if details:
        ex.details = details
    return ex


def _normalize_questions(questions: List[Dict[str, Any]]) -> List[QuestionConfigQuestion]:
    """
    Normalize questions to always have a number field.
    If questions don't have numbers, auto-generate them from array index (1-indexed).
    """
    normalized = []
    
    # Process questions with new format - map to internal schema
    for idx, q in enumerate(questions, start=1):
        normalized.append(QuestionConfigQuestion(
            question_id=q['question_number'],  # Use question_number as question_id
            number=idx,  # Auto-generate sequential numbers
            max_marks=q['max_mark']  # Map max_mark to max_marks
        ))
    
    return normalized


@router.post("/questions/config", response_model=OkRes)
def set_questions_config(payload: QuestionConfigReq) -> OkRes:
    # Validate session exists
    s = supabase.table("session").select("id").eq("id", payload.session_id).execute()
    if not s.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_id not found")

    # Normalize questions to ensure all have numbers
    normalized_questions = _normalize_questions(payload.questions)
    
    # Validate uniqueness of question_id
    seen_qids = set()
    question_info = {}
    for q in normalized_questions:
        if q.question_id in seen_qids:
            raise _bad_request(
                "duplicate question_id in questions",
                details={"question_id": q.question_id},
            )
        seen_qids.add(q.question_id)
        question_info[q.question_id] = q.max_marks

    # Validate human marks keys exist and are within [0, max_marks]
    for qid, mark in payload.human_marks_by_qid.items():
        if qid not in question_info:
            raise _bad_request(
                "human_marks_by_qid contains question_id not present in questions",
                details={"question_id": qid},
            )
        max_marks = question_info[qid]
        if mark < 0 or mark > max_marks:
            raise _bad_request(
                "mark out of range for question",
                details={"question_id": qid, "mark": mark, "max_marks": max_marks},
            )

    # Persistence
    # Upsert questions by (session_id, question_id). Also ensure uniqueness on (session_id, number) via DB constraint.
    question_rows = [
        {
            "session_id": payload.session_id,
            "question_id": q.question_id,
            "number": q.number,
            "max_marks": q.max_marks,
        }
        for q in normalized_questions
    ]

    try:
        # Use on_conflict to upsert by logical unique key
        supabase.table("question").upsert(question_rows, on_conflict="session_id,question_id").execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upsert questions: {e}")

    # Delete questions not present in the payload (payload authoritative)
    try:
        existing = (
            supabase.table("question")
            .select("question_id")
            .eq("session_id", payload.session_id)
            .execute()
        )
        existing_qids = {row["question_id"] for row in (existing.data or [])}
        desired_qids = {q.question_id for q in normalized_questions}
        to_delete = list(existing_qids - desired_qids)
        if to_delete:
            (
                supabase.table("question")
                .delete()
                .eq("session_id", payload.session_id)
                .in_("question_id", to_delete)
                .execute()
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete removed questions: {e}")

    # Upsert stats.human_marks_by_qid and update updated_at
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        supabase.table("stats").upsert(
            {
                "session_id": payload.session_id,
                "human_marks_by_qid": payload.human_marks_by_qid,
                "updated_at": now_iso,
            },
            on_conflict="session_id",
        ).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upsert stats: {e}")

    return OkRes(ok=True)


@router.get("/questions/{session_id}", response_model=QuestionsRes)
def get_questions(session_id: str) -> QuestionsRes:
    # Ensure session exists
    s = supabase.table("session").select("id").eq("id", session_id).execute()
    if not s.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_id not found")

    try:
        res = (
            supabase.table("question")
            .select("question_id,number,max_marks")
            .eq("session_id", session_id)
            .order("number")
            .execute()
        )
        rows = res.data or []
        questions = [
            QuestionConfigQuestion(
                question_id=str(r.get("question_id")),
                number=int(r.get("number")),
                max_marks=float(r.get("max_marks")),
            )
            for r in rows
            if r.get("question_id") is not None and r.get("number") is not None and r.get("max_marks") is not None
        ]
        return QuestionsRes(session_id=session_id, questions=questions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch questions: {e}")
