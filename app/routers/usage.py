import logging
import os

from fastapi import APIRouter

from ..supabase_client import supabase

router = APIRouter()

MB = 1024 * 1024


def _limit_bytes(env_name: str, default_mb: int) -> int:
    try:
        return int(float(os.getenv(env_name, default_mb)) * MB)
    except ValueError:
        return default_mb * MB


def _meter(used: int, limit: int) -> dict:
    return {
        "used_bytes": used,
        "limit_bytes": limit,
        "percent": round(used / limit * 100, 1) if limit else 0.0,
    }


@router.get("/usage")
def get_usage():
    """Database and Storage usage against the Supabase plan limits.

    Needs the get_usage_stats() function from migration 006. Egress isn't queryable
    from SQL, so it's only visible on the Supabase dashboard.
    """
    # Free-plan defaults; override when the project moves to a bigger plan.
    db_limit = _limit_bytes("SUPABASE_DB_LIMIT_MB", 500)
    storage_limit = _limit_bytes("SUPABASE_STORAGE_LIMIT_MB", 1024)
    warn_percent = float(os.getenv("USAGE_WARN_PERCENT", "80"))

    try:
        stats = supabase.rpc("get_usage_stats", {}).execute().data or {}
    except Exception as e:
        logging.warning("get_usage_stats RPC failed: %s", e)
        restricted = "restricted" in str(e).lower()
        if restricted:
            message = ("Supabase has restricted this project for going over a free-plan limit, so "
                       "assessments can't be loaded or graded until space is freed up.")
        else:
            message = "Usage stats unavailable. Apply migration 006_add_usage_stats_function.sql in Supabase."
        return {"available": False, "restricted": restricted, "message": message}

    return {
        "available": True,
        "warn_percent": warn_percent,
        "database": _meter(int(stats.get("db_bytes") or 0), db_limit),
        "storage": {
            **_meter(int(stats.get("storage_bytes") or 0), storage_limit),
            "objects": int(stats.get("storage_objects") or 0),
        },
    }
