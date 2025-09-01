from typing import Dict, List, Any

from fastapi import APIRouter, HTTPException, status

from ..schemas import ResultsRes, ResultItem, ResultsErrorsRes
from ..supabase_client import supabase


router = APIRouter()


@router.get("/results/{session_id}", response_model=ResultsRes)
def get_results(session_id: str) -> ResultsRes:
    # Validate session exists (consistent with other endpoints)
    s = supabase.table("session").select("id").eq("id", session_id).execute()
    if not s.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_id not found")

    # Read results for this session
    # We exclude special parse-error marker question_id if present
    res = (
        supabase.table("result")
        .select("question_id,model_name,try_index,marks_awarded,rubric_notes")
        .eq("session_id", session_id)
        .order("question_id")
        .order("model_name")
        .order("try_index")
        .execute()
    )

    results_by_question: Dict[str, Dict[str, List[ResultItem]]] = {}

    for row in res.data or []:
        qid = row.get("question_id")
        if qid == "__parse_error__":
            # Do not expose parse-error marker as a question id
            continue
        model = row.get("model_name")
        try_index = int(row.get("try_index")) if row.get("try_index") is not None else None
        item = ResultItem(
            try_index=try_index or 1,
            marks_awarded=(row.get("marks_awarded") if row.get("marks_awarded") is not None else None),
            rubric_notes=row.get("rubric_notes"),
        )
        if qid not in results_by_question:
            results_by_question[qid] = {}
        if model not in results_by_question[qid]:
            results_by_question[qid][model] = []
        results_by_question[qid][model].append(item)

    # Ensure lists are sorted by try_index ascending (defensive)
    for qid, models in results_by_question.items():
        for model, items in models.items():
            models[model] = sorted(items, key=lambda x: x.try_index)

    return ResultsRes(session_id=session_id, results_by_question=results_by_question)


@router.get("/results/errors/{session_id}", response_model=ResultsErrorsRes)
def get_result_errors(session_id: str) -> ResultsErrorsRes:
    # Validate session exists
    s = supabase.table("session").select("id").eq("id", session_id).execute()
    if not s.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_id not found")

    # First, find model/try pairs that already have valid answers
    valid_pairs: set[tuple[str, int]] = set()
    try:
        vres = (
            supabase.table("result")
            .select("model_name,try_index")
            .eq("session_id", session_id)
            .neq("question_id", "__parse_error__")
            .execute()
        )
        for r in vres.data or []:
            m = r.get("model_name")
            ti = int(r.get("try_index") or 1)
            if m is not None:
                valid_pairs.add((m, ti))
    except Exception:
        # If this query fails, fall back to returning all error rows
        valid_pairs = set()

    # Fetch rows that captured parse/validation errors
    res = (
        supabase.table("result")
        .select("model_name,try_index,validation_errors")
        .eq("session_id", session_id)
        .eq("question_id", "__parse_error__")
        .order("model_name")
        .order("try_index")
        .execute()
    )

    errors_by_model_try: dict[str, dict[str, list[dict]]] = {}
    for row in res.data or []:
        model = row.get("model_name")
        ti_int = int(row.get("try_index") or 1)
        # Skip stale error if we have valid answers for the same model/try
        if model is not None and (model, ti_int) in valid_pairs:
            continue
        try_index = str(ti_int)
        verr = row.get("validation_errors") or {}
        if model not in errors_by_model_try:
            errors_by_model_try[model] = {}
        if try_index not in errors_by_model_try[model]:
            errors_by_model_try[model][try_index] = []
        # Ensure list of dicts for UI consumption
        if isinstance(verr, list):
            for v in verr:
                if isinstance(v, dict):
                    errors_by_model_try[model][try_index].append(v)
                else:
                    errors_by_model_try[model][try_index].append({"reason": str(v)})
        elif isinstance(verr, dict):
            errors_by_model_try[model][try_index].append(verr)
        else:
            errors_by_model_try[model][try_index].append({"reason": str(verr)})

    return ResultsErrorsRes(session_id=session_id, errors_by_model_try=errors_by_model_try)
