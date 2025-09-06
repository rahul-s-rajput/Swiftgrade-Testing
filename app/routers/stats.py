from __future__ import annotations

from typing import Dict, List, Set, Any, Tuple

from fastapi import APIRouter, HTTPException, status

from ..schemas import StatsRes
from ..supabase_client import supabase


router = APIRouter()


def _zpf_tag(mark: float, max_marks: float) -> str:
    if max_marks <= 0:
        return "P"
    if mark <= 0:
        return "Z"
    if abs(mark - max_marks) < 1e-9:
        return "F"
    return "P"


def _range_bucket(mark: float, max_marks: float) -> str:
    if max_marks <= 0:
        return "25_74_9"
    pct = (mark / max_marks) * 100.0
    if pct <= 25.0:
        return "0_25"
    if pct >= 75.0:
        return "75_100"
    return "25_74_9"


@router.get("/stats/{session_id}", response_model=StatsRes)
def get_stats(session_id: str) -> StatsRes:
    # Validate session exists
    s = supabase.table("session").select("id").eq("id", session_id).execute()
    if not s.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_id not found")

    # Read human marks
    stats_row = (
        supabase.table("stats").select("human_marks_by_qid").eq("session_id", session_id).execute()
    )
    human_marks_by_qid: Dict[str, float] = {}
    if stats_row.data:
        # stats may return multiple, but we upsert per session_id; take first
        raw = stats_row.data[0] or {}
        human_marks_by_qid = raw.get("human_marks_by_qid") or {}

    # Read questions (max marks per qid)
    q_rows = (
        supabase.table("question")
        .select("question_id,max_marks")
        .eq("session_id", session_id)
        .execute()
    )
    q_max: Dict[str, float] = {row["question_id"]: float(row["max_marks"]) for row in (q_rows.data or [])}

    # Precompute human tags and human_lt100 set over known questions
    human_zpf: Dict[str, str] = {}
    human_range: Dict[str, str] = {}
    human_lt100: Set[str] = set()
    for qid, hmark in human_marks_by_qid.items():
        if qid not in q_max:
            continue
        maxm = q_max[qid]
        human_zpf[qid] = _zpf_tag(float(hmark), maxm)
        human_range[qid] = _range_bucket(float(hmark), maxm)
        if float(hmark) < maxm:
            human_lt100.add(qid)

    # Read AI results for this session
    res = (
        supabase.table("result")
        .select("question_id,model_name,try_index,marks_awarded")
        .eq("session_id", session_id)
        .order("model_name")
        .order("try_index")
        .order("question_id")
        .execute()
    )

    # Aggregate totals and per model/try structures
    totals_total_max = sum(q_max.values())
    totals_by_model_try: Dict[str, Dict[str, float]] = {}

    # For discrepancies we need, per model/try, ai marks per qid
    ai_marks: Dict[Tuple[str, int], Dict[str, float]] = {}

    for row in res.data or []:
        qid = row.get("question_id")
        if not qid or qid == "__parse_error__":
            continue
        if qid not in q_max:
            continue
        model = row.get("model_name")
        try_index = int(row.get("try_index") or 1)
        mark = row.get("marks_awarded")
        if mark is None:
            continue
        mark = float(mark)

        # totals
        if model not in totals_by_model_try:
            totals_by_model_try[model] = {}
        key_try = str(try_index)
        totals_by_model_try[model][key_try] = totals_by_model_try[model].get(key_try, 0.0) + mark

        # ai marks per question
        k = (model, try_index)
        if k not in ai_marks:
            ai_marks[k] = {}
        ai_marks[k][qid] = mark

    discrepancies_by_model_try: Dict[str, Dict[str, Any]] = {}

    for (model, try_index), qmarks in ai_marks.items():
        # Sets limited to qids where AI has marks (skip missing AI outputs per Acceptance Criteria)
        ai_qids: Set[str] = set(qmarks.keys())
        # lt100 sets
        ai_lt100: Set[str] = {qid for qid in ai_qids if qmarks[qid] < q_max[qid]}
        human_lt100_intersect: Set[str] = human_lt100.intersection(ai_qids)
        lt100_symdiff = sorted(list(ai_lt100.symmetric_difference(human_lt100_intersect)))

        # zpf mismatches
        zpf_mismatched = []
        zpf_questions = []
        for qid in sorted(ai_qids):
            maxm = q_max[qid]
            ai_tag = _zpf_tag(qmarks[qid], maxm)
            h_tag = human_zpf.get(qid)
            if h_tag is None:
                continue
            if ai_tag != h_tag:
                zpf_mismatched.append({"qid": qid, "human": h_tag, "ai": ai_tag})
                zpf_questions.append(qid)

        # range mismatches
        range_mismatched = []
        range_questions = []
        for qid in sorted(ai_qids):
            maxm = q_max[qid]
            ai_tag = _range_bucket(qmarks[qid], maxm)
            h_tag = human_range.get(qid)
            if h_tag is None:
                continue
            if ai_tag != h_tag:
                range_mismatched.append({"qid": qid, "human": h_tag, "ai": ai_tag})
                range_questions.append(qid)

        if model not in discrepancies_by_model_try:
            discrepancies_by_model_try[model] = {}
        discrepancies_by_model_try[model][str(try_index)] = {
            "lt100": {"count": len(lt100_symdiff), "questions": lt100_symdiff},
            "zpf": {"count": len(zpf_mismatched), "questions": zpf_questions, "mismatched": zpf_mismatched},
            "range": {
                "count": len(range_mismatched),
                "questions": range_questions,
                "mismatched": range_mismatched,
            },
        }

    # Read token usage statistics
    token_usage_stats = {}
    try:
        token_res = (
            supabase.table("token_usage")
            .select("model_name,try_index,input_tokens,output_tokens,reasoning_tokens,total_tokens,cost_estimate")
            .eq("session_id", session_id)
            .execute()
        )
        
        # Aggregate token usage by model
        for row in token_res.data or []:
            model = row.get("model_name")
            try_index = row.get("try_index")
            if model and try_index is not None:
                if model not in token_usage_stats:
                    token_usage_stats[model] = {
                        "total_input_tokens": 0,
                        "total_output_tokens": 0,
                        "total_reasoning_tokens": 0,
                        "total_tokens": 0,
                        "total_cost": 0.0,
                        "attempts": {}
                    }
                
                # Add to totals
                token_usage_stats[model]["total_input_tokens"] += row.get("input_tokens", 0)
                token_usage_stats[model]["total_output_tokens"] += row.get("output_tokens", 0)
                token_usage_stats[model]["total_reasoning_tokens"] += row.get("reasoning_tokens", 0) or 0
                token_usage_stats[model]["total_tokens"] += row.get("total_tokens", 0)
                token_usage_stats[model]["total_cost"] += row.get("cost_estimate", 0.0) or 0.0
                
                # Store per-attempt data
                token_usage_stats[model]["attempts"][str(try_index)] = {
                    "input_tokens": row.get("input_tokens", 0),
                    "output_tokens": row.get("output_tokens", 0),
                    "reasoning_tokens": row.get("reasoning_tokens"),
                    "total_tokens": row.get("total_tokens", 0),
                    "cost_estimate": row.get("cost_estimate")
                }
    except Exception:
        # If token_usage table doesn't exist or query fails, continue without token stats
        pass
    
    totals = {
        "total_max_marks": totals_total_max,
        "total_marks_awarded_by_model_try": totals_by_model_try,
        "token_usage_stats": token_usage_stats
    }

    # Persist the computed stats so the 'stats' table stores totals and discrepancies
    try:
        supabase.table("stats").upsert(
            {
                "session_id": session_id,
                "human_marks_by_qid": human_marks_by_qid,
                "totals": totals,
                "discrepancies_by_model_try": discrepancies_by_model_try,
            },
            on_conflict="session_id",
        ).execute()
    except Exception:
        # Non-fatal: still return computed stats to caller
        pass

    return StatsRes(
        session_id=session_id,
        human_marks_by_qid=human_marks_by_qid,
        totals=totals,
        discrepancies_by_model_try=discrepancies_by_model_try,
    )
