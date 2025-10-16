from typing import Dict, List, Any

from fastapi import APIRouter, HTTPException, status

from ..schemas import ResultsRes, ResultItem, ResultsErrorsRes, TokenUsageItem, RubricResultsRes, RubricResultItem
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
    
    # Read token usage for this session
    token_usage_data = {}
    try:
        token_res = (
            supabase.table("token_usage")
            .select("model_name,try_index,input_tokens,output_tokens,reasoning_tokens,total_tokens,cost_estimate")
            .eq("session_id", session_id)
            .execute()
        )
        
        # Index token usage by model_name and try_index for quick lookup
        for row in token_res.data or []:
            model = row.get("model_name")
            try_index = row.get("try_index")
            if model and try_index is not None:
                key = f"{model}_{try_index}"
                token_usage_data[key] = TokenUsageItem(
                    input_tokens=row.get("input_tokens", 0),
                    output_tokens=row.get("output_tokens", 0),
                    reasoning_tokens=row.get("reasoning_tokens"),
                    total_tokens=row.get("total_tokens", 0),
                    cost_estimate=row.get("cost_estimate")
                )
    except Exception:
        # If token_usage table doesn't exist or query fails, continue without token data
        pass

    results_by_question: Dict[str, Dict[str, List[ResultItem]]] = {}

    for row in res.data or []:
        qid = row.get("question_id")
        if qid == "__parse_error__":
            # Do not expose parse-error marker as a question id
            continue
        model = row.get("model_name")
        try_index = int(row.get("try_index")) if row.get("try_index") is not None else None
        # Look up token usage for this model and try_index
        token_usage_key = f"{model}_{try_index or 1}"
        token_usage = token_usage_data.get(token_usage_key)
        
        item = ResultItem(
            try_index=try_index or 1,
            marks_awarded=(row.get("marks_awarded") if row.get("marks_awarded") is not None else None),
            rubric_notes=row.get("rubric_notes"),
            token_usage=token_usage
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


@router.get("/results/{session_id}/rubric", response_model=RubricResultsRes)
def get_rubric_results(session_id: str) -> RubricResultsRes:
    """Get rubric analysis results for a session.
    
    Returns rubric responses organized by model and try index.
    This endpoint is used to display rubric analysis in the UI.
    """
    # Validate session exists
    s = supabase.table("session").select("id").eq("id", session_id).execute()
    if not s.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_id not found")
    
    # Read rubric results for this session
    res = (
        supabase.table("rubric_result")
        .select("model_name,try_index,rubric_response,validation_errors")
        .eq("session_id", session_id)
        .order("model_name")
        .order("try_index")
        .execute()
    )
    
    rubric_results: Dict[str, Dict[str, RubricResultItem]] = {}
    
    for row in res.data or []:
        model = row.get("model_name")
        try_index = int(row.get("try_index")) if row.get("try_index") is not None else 1
        try_index_str = str(try_index)
        
        item = RubricResultItem(
            try_index=try_index,
            rubric_response=row.get("rubric_response"),
            validation_errors=row.get("validation_errors")
        )
        
        if model not in rubric_results:
            rubric_results[model] = {}
        
        rubric_results[model][try_index_str] = item
    
    return RubricResultsRes(session_id=session_id, rubric_results=rubric_results)
