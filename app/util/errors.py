from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import uuid


def _correlation_id_from_request(request: Request) -> str:
    return request.headers.get("X-Request-ID") or str(uuid.uuid4())


async def http_exception_handler(request: Request, exc: HTTPException):
    cid = _correlation_id_from_request(request)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": getattr(exc, "code", "HTTP_ERROR"),
                "message": exc.detail if isinstance(getattr(exc, "detail", None), str) else str(getattr(exc, "detail", exc)),
                "details": getattr(exc, "details", None),
                "correlation_id": cid,
            }
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    cid = _correlation_id_from_request(request)
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
    )


async def general_exception_handler(request: Request, exc: Exception):
    cid = _correlation_id_from_request(request)
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
    )
