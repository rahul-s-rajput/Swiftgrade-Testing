import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv

from .util.errors import http_exception_handler, validation_exception_handler, general_exception_handler
from .routers import sessions as sessions_router
from .routers import images as images_router
from .routers import questions as questions_router
from .routers import grade as grade_router
from .routers import results as results_router
from .routers import stats as stats_router
from .routers import settings as settings_router


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    env_origins = [o.strip() for o in raw.split(",") if o.strip()]
    defaults = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    # Merge env-provided origins with defaults, preserving order and removing duplicates
    seen: set[str] = set()
    combined: list[str] = []
    for o in env_origins + defaults:
        if o and o not in seen:
            combined.append(o)
            seen.add(o)
    return combined


def _cors_regex() -> str | None:
    # Optional regex via env; defaults to allowing localhost/127.0.0.1 with any port
    rx = os.getenv("CORS_ORIGIN_REGEX", None)
    if rx and rx.strip():
        return rx.strip()
    # Allow typical local dev origins e.g., http://localhost:5173, http://127.0.0.1:5173
    return r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"


load_dotenv()  # load .env if present

# Basic logging so router logs (INFO) are visible; allow override via LOG_LEVEL
try:
    _lvl = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=getattr(logging, _lvl, logging.INFO), format="%(asctime)s %(levelname)s %(message)s")
except Exception:
    pass

app = FastAPI(title="Essay Grading Prototype Backend")

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=_cors_regex(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Error handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


@app.get("/health")
def health():
    return {"ok": True}


# Routers
app.include_router(sessions_router.router)
app.include_router(images_router.router)
app.include_router(questions_router.router)
app.include_router(grade_router.router)
app.include_router(results_router.router)
app.include_router(stats_router.router)
app.include_router(settings_router.router)
