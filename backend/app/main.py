from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError, register_exception_handlers
from app.api.responses import envelope
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.middleware import SecurityMiddleware
from app.db.session import engine, get_session


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        yield
        otp_store = getattr(application.state, "otp_store", None)
        close_store = getattr(otp_store, "aclose", None)
        if close_store is not None:
            await close_store()
        otp_sender = getattr(application.state, "otp_sender", None)
        close_sender = getattr(otp_sender, "aclose", None)
        if close_sender is not None:
            await close_sender()
        await engine.dispose()

    app = FastAPI(title="Livestock Health API", version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        SecurityMiddleware,
        production=active_settings.is_production,
        max_request_body_bytes=active_settings.max_request_body_bytes,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "If-Match"],
    )
    register_exception_handlers(
        app,
        expose_internal_errors=not active_settings.is_production,
    )
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    async def health(
        request: Request,
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> dict[str, object]:
        try:
            await session.execute(text("SELECT 1"))
        except SQLAlchemyError as error:
            raise ApiError(
                503,
                "DATABASE_UNAVAILABLE",
                "The service is temporarily unavailable.",
            ) from error
        return envelope(
            {"status": "healthy"},
            meta={"request_id": request.state.request_id},
        )

    return app


app = create_app()
