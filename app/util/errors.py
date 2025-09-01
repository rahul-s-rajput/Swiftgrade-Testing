from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import re
from fastapi.exceptions import RequestValidationError
import uuid
import logging


def _correlation_id_from_request(request: Request) -> str:
    return request.headers.get("X-Request-ID") or str(uuid.uuid4())


async def http_exception_handler(request: Request, exc: HTTPException):
    cid = _correlation_id_from_request(request)
    status = exc.status_code
    # Map standard codes if not provided
    code = getattr(exc, "code", None)
    if not code:
        if status == 404:
            code = "NOT_FOUND"
        elif status == 401:
            code = "UNAUTHORIZED"
        elif status == 429:
            code = "RATE_LIMITED"
        else:
            code = "HTTP_ERROR"

    message = exc.detail if isinstance(getattr(exc, "detail", None), str) else str(getattr(exc, "detail", exc))
    details = getattr(exc, "details", None)

    logging.error(f"HTTPException status={status} code={code} cid={cid} message={message}")

    # Ensure CORS headers on error responses for local dev
    origin = request.headers.get("origin")
    base_headers = getattr(exc, "headers", None) or {}
    headers = dict(base_headers) if isinstance(base_headers, dict) else {}
    if origin and (origin in (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ) or re.match(r"^https?://(localhost|127\.0\.0\.1)(:\\d+)?$", origin)):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"

    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "correlation_id": cid,
            }
        },
        headers=headers,  # propagate Retry-After + CORS
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    cid = _correlation_id_from_request(request)
    logging.warning(f"Validation error cid={cid} errors={exc.errors()}")
    origin = request.headers.get("origin")
    headers = {}
    if origin and (origin in (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ) or re.match(r"^https?://(localhost|127\.0\.0\.1)(:\\d+)?$", origin)):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request payload",
                "details": {"errors": exc.errors()},
                "correlation_id": cid,
            }
        },
        headers=headers,
    )


async def general_exception_handler(request: Request, exc: Exception):
    cid = _correlation_id_from_request(request)
    logging.exception(f"Unhandled exception cid={cid}")
    origin = request.headers.get("origin")
    headers = {}
    if origin and (origin in (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ) or re.match(r"^https?://(localhost|127\.0\.0\.1)(:\\d+)?$", origin)):
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc) or "Internal Server Error",
                "details": None,
                "correlation_id": cid,
            }
        },
        headers=headers,
    )
