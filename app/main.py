import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv

from .util.errors import http_exception_handler, validation_exception_handler, general_exception_handler
from .routers import sessions as sessions_router
from .routers import images as images_router
from .routers import questions as questions_router


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174")
    return [o.strip() for o in raw.split(",") if o.strip()]


load_dotenv()  # load .env if present

app = FastAPI(title="Essay Grading Prototype Backend")

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
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
