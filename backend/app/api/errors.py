import logging
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ApiError(Exception):
    status_code: int
    code: str
    message: str


def error_envelope(request: Request, code: str, message: str) -> dict[str, Any]:
    return {
        "data": None,
        "meta": {"request_id": request.state.request_id},
        "error": {"code": code, "message": message},
    }


def register_exception_handlers(app: FastAPI, *, expose_internal_errors: bool) -> None:
    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, error: IntegrityError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content=error_envelope(
                request, "CONFLICT", "The request conflicts with existing data."
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, error: StarletteHTTPException) -> JSONResponse:
        messages = {
            404: ("NOT_FOUND", "The requested resource was not found."),
            405: ("METHOD_NOT_ALLOWED", "The request method is not allowed."),
        }
        code, message = messages.get(
            error.status_code, ("HTTP_ERROR", "The request could not be completed.")
        )
        return JSONResponse(
            status_code=error.status_code,
            content=error_envelope(request, code, message),
            headers=error.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_envelope(
                request,
                "VALIDATION_ERROR",
                "The request did not satisfy the required schema.",
            ),
        )

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, error: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content=error_envelope(request, error.code, error.message),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        logger.error(
            "Unhandled API error (request_id=%s, type=%s)",
            request.state.request_id,
            type(error).__name__,
        )
        message = str(error) if expose_internal_errors else "An unexpected error occurred."
        return JSONResponse(
            status_code=500,
            content=error_envelope(request, "INTERNAL_ERROR", message),
        )
