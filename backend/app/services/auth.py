import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol
from uuid import UUID

import httpx
import jwt
import pyotp
from redis.asyncio import Redis
from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.crypto import (
    DUMMY_PASSWORD_HASH,
    decode_jwt,
    decrypt_secret,
    encode_jwt,
    generate_otp,
    hash_refresh_token,
    normalize_mobile_number,
    otp_digest,
    verify_password,
)
from app.db.base import utc_now, uuid7
from app.models.geography import Location, StaffGeographicAssignment
from app.models.identity import (
    AuthIdentity,
    MfaChallenge,
    MfaCredential,
    RefreshSession,
    Role,
    User,
    UserRole,
)


class AuthenticationError(Exception):
    pass


class RateLimitError(Exception):
    pass


class OtpDeliveryError(Exception):
    pass


class OtpStore(Protocol):
    async def store(self, key: str, digest: str, ttl_seconds: int) -> None: ...

    async def consume(self, key: str) -> str | None: ...

    async def increment(self, key: str, window_seconds: int) -> int: ...


class OtpSender(Protocol):
    async def send(self, mobile_number: str, code: str) -> None: ...


class RedisOtpStore:
    def __init__(self, client: Redis) -> None:
        self.client = client

    async def store(self, key: str, digest: str, ttl_seconds: int) -> None:
        await self.client.set(key, digest, ex=ttl_seconds)

    async def consume(self, key: str) -> str | None:
        value = await self.client.getdel(key)
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else str(value)

    async def increment(self, key: str, window_seconds: int) -> int:
        async with self.client.pipeline(transaction=True) as pipeline:
            pipeline.incr(key)
            pipeline.expire(key, window_seconds, nx=True)
            count, _ = await pipeline.execute()
        return int(count)

    async def aclose(self) -> None:
        await self.client.aclose()


class HttpOtpSender:
    def __init__(self, url: str, bearer_token: str) -> None:
        self.url = url
        self.bearer_token = bearer_token
        self.client = httpx.AsyncClient(timeout=10)

    async def send(self, mobile_number: str, code: str) -> None:
        try:
            response = await self.client.post(
                self.url,
                headers={"Authorization": f"Bearer {self.bearer_token}"},
                json={"mobile_number": mobile_number, "code": code},
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise OtpDeliveryError("The OTP delivery service is unavailable.") from error

    async def aclose(self) -> None:
        await self.client.aclose()


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    access_expires_in: int


@dataclass(frozen=True, slots=True)
class CurrentPrincipal:
    user_id: UUID
    roles: tuple[str, ...]
    location_path: str | None


def _otp_key(mobile_number: str, device_id: str) -> str:
    return f"otp:{mobile_number}:{device_id}"


async def request_farmer_otp(
    store: OtpStore,
    sender: OtpSender,
    *,
    mobile_number: str,
    device_id: str,
    client_ip: str,
    settings: Settings,
) -> str:
    normalized = normalize_mobile_number(mobile_number)
    limits = (
        (f"otp-limit:mobile:{normalized}", 5),
        (f"otp-limit:device:{device_id}", 10),
        (f"otp-limit:ip:{client_ip}", 20),
    )
    for key, maximum in limits:
        if await store.increment(key, 900) > maximum:
            raise RateLimitError("Too many OTP requests. Try again later.")

    code = generate_otp()
    digest = otp_digest(normalized, device_id, code, settings.otp_hmac_key)
    await store.store(_otp_key(normalized, device_id), digest, settings.otp_ttl_seconds)
    await sender.send(normalized, code)
    return normalized


async def _roles_and_path(
    session: AsyncSession, user_id: UUID
) -> tuple[tuple[str, ...], str | None]:
    roles = tuple(
        (
            await session.scalars(
                select(Role.code)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user_id)
                .order_by(Role.code)
            )
        ).all()
    )
    location_path = await session.scalar(
        select(Location.hierarchy_path)
        .join(
            StaffGeographicAssignment,
            StaffGeographicAssignment.location_id == Location.id,
        )
        .where(
            StaffGeographicAssignment.user_id == user_id,
            StaffGeographicAssignment.active.is_(True),
        )
    )
    return roles, location_path


async def issue_token_pair(
    session: AsyncSession,
    user: User,
    device_id: str,
    settings: Settings,
    *,
    family_id: UUID | None = None,
    rotated_from_id: UUID | None = None,
) -> TokenPair:
    roles, location_path = await _roles_and_path(session, user.id)
    expires_in = settings.access_token_minutes * 60
    access_token = encode_jwt(
        subject=user.id,
        signing_key=settings.jwt_signing_key,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        lifetime=timedelta(minutes=settings.access_token_minutes),
        purpose="access",
        claims={"roles": list(roles), "location_path": location_path},
    )
    raw_refresh = secrets.token_urlsafe(48)
    session.add(
        RefreshSession(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh, settings.refresh_token_pepper),
            family_id=family_id or uuid7(),
            rotated_from_id=rotated_from_id,
            device_id=device_id,
            expires_at=utc_now() + timedelta(days=settings.refresh_token_days),
            reuse_detected=False,
        )
    )
    await session.flush()
    return TokenPair(access_token, raw_refresh, expires_in)


async def verify_farmer_otp(
    session: AsyncSession,
    store: OtpStore,
    *,
    mobile_number: str,
    device_id: str,
    code: str,
    settings: Settings,
) -> tuple[User, TokenPair]:
    normalized = normalize_mobile_number(mobile_number)
    stored = await store.consume(_otp_key(normalized, device_id))
    candidate = otp_digest(normalized, device_id, code, settings.otp_hmac_key)
    if stored is None or not hmac.compare_digest(stored, candidate):
        raise AuthenticationError("The OTP is invalid or expired.")

    user = await session.scalar(select(User).where(User.mobile_number == normalized))
    if user is None:
        user = User(user_type="FARMER", mobile_number=normalized, display_name=normalized)
        farmer_role = await session.scalar(select(Role).where(Role.code == "FARMER"))
        if farmer_role is None:
            farmer_role = Role(code="FARMER", description="Livestock owner or farmer")
            session.add(farmer_role)
        session.add(user)
        await session.flush()
        session.add(UserRole(user_id=user.id, role_id=farmer_role.id))
        await session.flush()
    if not user.is_active:
        raise AuthenticationError("The account is inactive.")
    return user, await issue_token_pair(session, user, device_id, settings)


async def refresh_tokens(
    session: AsyncSession,
    *,
    raw_token: str,
    device_id: str,
    settings: Settings,
) -> tuple[User, TokenPair]:
    token_hash = hash_refresh_token(raw_token, settings.refresh_token_pepper)
    stored = await session.scalar(
        select(RefreshSession).where(RefreshSession.token_hash == token_hash).with_for_update()
    )
    if stored is None:
        raise AuthenticationError("The refresh token is invalid.")
    if stored.revoked_at is not None:
        now = utc_now()
        await session.execute(
            update(RefreshSession)
            .where(RefreshSession.family_id == stored.family_id)
            .values(revoked_at=now, reuse_detected=True)
        )
        await session.flush()
        raise AuthenticationError("Refresh-token replay was detected.")
    if stored.device_id != device_id or stored.expires_at <= utc_now():
        stored.revoked_at = utc_now()
        await session.flush()
        raise AuthenticationError("The refresh token is invalid or expired.")

    user = await session.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("The account is inactive.")
    stored.revoked_at = utc_now()
    pair = await issue_token_pair(
        session,
        user,
        device_id,
        settings,
        family_id=stored.family_id,
        rotated_from_id=stored.id,
    )
    return user, pair


async def authenticate_staff_password(
    session: AsyncSession, staff_identifier: str, password: str, settings: Settings
) -> str:
    user = await session.scalar(
        select(User).where(User.staff_identifier == staff_identifier.strip())
    )
    identity = (
        await session.scalar(
            select(AuthIdentity).where(AuthIdentity.user_id == user.id).with_for_update()
        )
        if user
        else None
    )
    now = utc_now()
    if identity is not None and identity.locked_until is not None and identity.locked_until > now:
        raise AuthenticationError("The staff account is temporarily locked.")
    candidate_hash = (
        identity.password_hash
        if identity is not None and identity.password_hash is not None
        else DUMMY_PASSWORD_HASH
    )
    password_is_valid = verify_password(password, candidate_hash)
    if (
        user is None
        or not user.is_active
        or identity is None
        or identity.password_hash is None
        or not password_is_valid
    ):
        if identity is not None:
            identity.failed_attempts += 1
            if identity.failed_attempts >= 5:
                identity.locked_until = now + timedelta(minutes=15)
            await session.flush()
        raise AuthenticationError("Invalid staff credentials.")
    identity.failed_attempts = 0
    identity.locked_until = None
    await session.execute(
        delete(MfaChallenge).where(
            MfaChallenge.user_id == user.id,
            or_(MfaChallenge.used_at.is_not(None), MfaChallenge.expires_at <= now),
        )
    )
    await session.flush()
    challenge = MfaChallenge(
        user_id=user.id,
        expires_at=now + timedelta(minutes=5),
    )
    session.add(challenge)
    await session.flush()
    return encode_jwt(
        subject=user.id,
        signing_key=settings.jwt_signing_key,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        lifetime=timedelta(minutes=5),
        purpose="mfa_challenge",
        claims={"jti": str(challenge.id)},
    )


async def verify_staff_mfa(
    session: AsyncSession,
    challenge_token: str,
    code: str,
    device_id: str,
    settings: Settings,
) -> tuple[User, TokenPair]:
    try:
        payload = decode_jwt(
            challenge_token,
            signing_key=settings.jwt_signing_key,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            purpose="mfa_challenge",
        )
    except jwt.InvalidTokenError as error:
        raise AuthenticationError("The MFA challenge is invalid or expired.") from error
    try:
        user_id = UUID(payload["sub"])
        challenge_id = UUID(payload["jti"])
    except (KeyError, ValueError) as error:
        raise AuthenticationError("The MFA challenge is invalid or expired.") from error
    challenge = await session.scalar(
        select(MfaChallenge).where(MfaChallenge.id == challenge_id).with_for_update()
    )
    if (
        challenge is None
        or challenge.user_id != user_id
        or challenge.used_at is not None
        or challenge.expires_at <= utc_now()
    ):
        raise AuthenticationError("The MFA challenge is invalid or expired.")
    user = await session.get(User, user_id)
    credential = await session.scalar(select(MfaCredential).where(MfaCredential.user_id == user_id))
    if user is None or not user.is_active or credential is None or credential.verified_at is None:
        raise AuthenticationError("MFA is not enrolled.")
    secret = decrypt_secret(credential.totp_secret_encrypted, settings.mfa_encryption_key)
    if not pyotp.TOTP(secret).verify(code, valid_window=1):
        raise AuthenticationError("The MFA code is invalid.")
    challenge.used_at = utc_now()
    await session.flush()
    return user, await issue_token_pair(session, user, device_id, settings)


async def principal_from_access_token(token: str, settings: Settings) -> CurrentPrincipal:
    try:
        payload = decode_jwt(
            token,
            signing_key=settings.jwt_signing_key,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            purpose="access",
        )
        return CurrentPrincipal(
            user_id=UUID(payload["sub"]),
            roles=tuple(payload.get("roles", [])),
            location_path=payload.get("location_path"),
        )
    except (jwt.InvalidTokenError, KeyError, ValueError) as error:
        raise AuthenticationError("The access token is invalid or expired.") from error
