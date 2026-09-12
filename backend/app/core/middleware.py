import re
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: object,
        *,
        production: bool = False,
        max_request_body_bytes: int = 1_048_576,
    ) -> None:
        super().__init__(app)
        self.production = production
        self.max_request_body_bytes = max_request_body_bytes

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        supplied_request_id = request.headers.get("x-request-id", "")
        request_id = (
            supplied_request_id
            if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", supplied_request_id)
            else str(uuid4())
        )
        request.state.request_id = request_id
        raw_content_length = request.headers.get("content-length")
        try:
            content_length = int(raw_content_length) if raw_content_length is not None else 0
        except ValueError:
            content_length = -1
        if content_length < 0:
            response = JSONResponse(
                status_code=400,
                content={
                    "data": None,
                    "meta": {"request_id": request_id},
                    "error": {
                        "code": "INVALID_CONTENT_LENGTH",
                        "message": "Content-Length must be a non-negative integer.",
                    },
                },
            )
        elif content_length > self.max_request_body_bytes:
            response = JSONResponse(
                status_code=413,
                content={
                    "data": None,
                    "meta": {"request_id": request_id},
                    "error": {
                        "code": "REQUEST_TOO_LARGE",
                        "message": "The request body is too large.",
                    },
                },
            )
        else:
            response = await call_next(request)
        response.headers["x-request-id"] = request_id
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["referrer-policy"] = "no-referrer"
        response.headers["cache-control"] = "no-store"
        response.headers["content-security-policy"] = "default-src 'none'; frame-ancestors 'none'"
        if self.production:
            response.headers["strict-transport-security"] = "max-age=31536000; includeSubDomains"
        return response
