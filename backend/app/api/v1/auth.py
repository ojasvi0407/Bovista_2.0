from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentPrincipalDependency
from app.api.errors import ApiError
from app.api.responses import envelope
from app.core.config import Settings, get_settings
from app.core.crypto import hash_refresh_token
from app.db.base import utc_now
from app.db.session import get_session
from app.models.identity import RefreshSession, User
from app.schemas.auth import (
    LogoutRequest,
    OtpRequest,
    OtpVerify,
    RefreshRequest,
    StaffLogin,
    StaffMfaVerify,
    TokenResponse,
)
from app.services.auth import (
    AuthenticationError,
    HttpOtpSender,
    LogOtpSender,
    OtpDeliveryError,
    OtpSender,
    OtpStore,
    RateLimitError,
    RedisOtpStore,
    TokenPair,
    authenticate_staff_password,
    refresh_tokens,
    request_farmer_otp,
    verify_farmer_otp,
    verify_staff_mfa,
)
from app.services.trust import record_audit

router = APIRouter(prefix="/auth", tags=["authentication"])


class MissingOtpSender:
    async def send(self, mobile_number: str, code: str) -> None:
        raise OtpDeliveryError("An OTP delivery adapter has not been configured.")


def _otp_store(request: Request, settings: Settings) -> OtpStore:
    configured = getattr(request.app.state, "otp_store", None)
    if configured is not None:
        return configured
    redis_client = Redis.from_url(settings.redis_url.get_secret_value())
    store = RedisOtpStore(redis_client)
    request.app.state.otp_store = store
    return store


def _otp_sender(request: Request, settings: Settings) -> OtpSender:
    configured = getattr(request.app.state, "otp_sender", None)
    if configured is not None:
        return configured
    if settings.otp_delivery_url and settings.otp_delivery_token:
        sender = HttpOtpSender(
            settings.otp_delivery_url,
            settings.otp_delivery_token.get_secret_value(),
        )
        request.app.state.otp_sender = sender
        return sender
    if settings.environment == "development" and settings.local_otp_logging:
        sender = LogOtpSender()
        request.app.state.otp_sender = sender
        return sender
    return MissingOtpSender()


def _token_data(pair: TokenPair) -> dict[str, Any]:
    return TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        access_expires_in=pair.access_expires_in,
    ).model_dump()


@router.post("/otp/request", status_code=status.HTTP_202_ACCEPTED)
async def otp_request(
    payload: OtpRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    try:
        await request_farmer_otp(
            _otp_store(request, settings),
            _otp_sender(request, settings),
            mobile_number=payload.mobile_number,
            device_id=payload.device_id,
            client_ip=request.client.host if request.client else "unknown",
            settings=settings,
        )
        await record_audit(session, None, "auth.otp.request", "user", None, True)
        await session.commit()
    except RateLimitError as error:
        await record_audit(session, None, "auth.otp.request", "user", None, False)
        await session.commit()
        raise ApiError(429, "OTP_RATE_LIMITED", str(error)) from error
    except OtpDeliveryError as error:
        await record_audit(session, None, "auth.otp.request", "user", None, False)
        await session.commit()
        raise ApiError(503, "OTP_DELIVERY_UNAVAILABLE", str(error)) from error
    except ValueError as error:
        raise ApiError(422, "INVALID_MOBILE_NUMBER", str(error)) from error
    return envelope({"accepted": True})


@router.post("/otp/verify")
async def otp_verify(
    payload: OtpVerify,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    try:
        user, pair = await verify_farmer_otp(
            session,
            _otp_store(request, settings),
            mobile_number=payload.mobile_number,
            device_id=payload.device_id,
            code=payload.code,
            settings=settings,
        )
        await record_audit(session, user.id, "auth.otp.verify", "user", user.id, True)
        await session.commit()
        return envelope(_token_data(pair))
    except AuthenticationError as error:
        await session.rollback()
        await record_audit(session, None, "auth.otp.verify", "user", None, False)
        await session.commit()
        raise ApiError(401, "INVALID_OTP", str(error)) from error
    except ValueError as error:
        raise ApiError(422, "INVALID_MOBILE_NUMBER", str(error)) from error


@router.post("/staff/login")
async def staff_login(
    payload: StaffLogin,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    try:
        challenge = await authenticate_staff_password(
            session, payload.staff_identifier, payload.password, settings
        )
        await record_audit(session, None, "auth.staff.password", "user", None, True)
        await session.commit()
        return envelope({"mfa_required": True, "challenge_token": challenge})
    except AuthenticationError as error:
        await record_audit(session, None, "auth.staff.password", "user", None, False)
        await session.commit()
        raise ApiError(401, "INVALID_STAFF_CREDENTIALS", str(error)) from error


@router.post("/staff/mfa/verify")
async def staff_mfa_verify(
    payload: StaffMfaVerify,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    try:
        user, pair = await verify_staff_mfa(
            session,
            payload.challenge_token,
            payload.code,
            payload.device_id,
            settings,
        )
        await record_audit(session, user.id, "auth.staff.mfa", "user", user.id, True)
        await session.commit()
        return envelope(_token_data(pair))
    except AuthenticationError as error:
        await record_audit(session, None, "auth.staff.mfa", "user", None, False)
        await session.commit()
        raise ApiError(401, "INVALID_MFA", str(error)) from error


@router.post("/refresh")
async def refresh(
    payload: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    try:
        user, pair = await refresh_tokens(
            session,
            raw_token=payload.refresh_token,
            device_id=payload.device_id,
            settings=settings,
        )
        await record_audit(session, user.id, "auth.refresh", "session", None, True)
        await session.commit()
        return envelope(_token_data(pair))
    except AuthenticationError as error:
        # Replay revocation is a security write and must survive the rejected request.
        await record_audit(session, None, "auth.refresh", "session", None, False)
        await session.commit()
        raise ApiError(401, "INVALID_REFRESH_TOKEN", str(error)) from error


@router.post("/logout")
async def logout(
    payload: LogoutRequest,
    principal: CurrentPrincipalDependency,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    token_hash = hash_refresh_token(payload.refresh_token, settings.refresh_token_pepper)
    stored = await session.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == token_hash,
            RefreshSession.user_id == principal.user_id,
        )
    )
    if stored is not None:
        await session.execute(
            update(RefreshSession)
            .where(RefreshSession.family_id == stored.family_id)
            .values(revoked_at=utc_now())
        )
    await record_audit(
        session, principal.user_id, "auth.logout", "session", stored.id if stored else None, True
    )
    await session.commit()
    return envelope({"logged_out": True})


@router.get("/me")
async def me(
    principal: CurrentPrincipalDependency,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    user = await session.get(User, principal.user_id)
    if user is None or not user.is_active:
        raise ApiError(401, "INACTIVE_ACCOUNT", "The account is inactive.")
    return envelope(
        {
            "user_id": str(user.id),
            "display_name": user.display_name,
            "roles": list(principal.roles),
            "location_path": principal.location_path,
        }
    )
