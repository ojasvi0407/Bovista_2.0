from collections.abc import AsyncIterator
from datetime import timedelta

import pyotp
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.crypto import encode_jwt, encrypt_secret, password_hasher
from app.db.base import utc_now
from app.db.session import get_session
from app.main import create_app
from app.models.geography import Location, StaffGeographicAssignment
from app.models.identity import AuthIdentity, MfaCredential, Role, User, UserRole


class CapturingOtpSender:
    def __init__(self) -> None:
        self.last_code: str | None = None

    async def send(self, mobile_number: str, code: str) -> None:
        self.last_code = code


class MemoryOtpStore:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.counters: dict[str, int] = {}

    async def store(self, key: str, digest: str, ttl_seconds: int) -> None:
        self.values[key] = digest

    async def consume(self, key: str) -> str | None:
        return self.values.pop(key, None)

    async def increment(self, key: str, window_seconds: int) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]


@pytest.fixture
async def auth_client(session) -> AsyncIterator[tuple[AsyncClient, CapturingOtpSender]]:
    application = create_app()
    sender = CapturingOtpSender()
    application.state.otp_sender = sender
    application.state.otp_store = MemoryOtpStore()

    async def override_session():
        yield session

    application.dependency_overrides[get_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://testserver",
    ) as client:
        yield client, sender


@pytest.mark.asyncio
async def test_farmer_otp_is_single_use(auth_client) -> None:
    client, otp_sender = auth_client
    response = await client.post(
        "/api/v1/auth/otp/request",
        json={"mobile_number": "+919999999999", "device_id": "phone-1"},
    )
    assert response.status_code == 202
    assert otp_sender.last_code is not None

    payload = {
        "mobile_number": "+919999999999",
        "code": otp_sender.last_code,
        "device_id": "phone-1",
    }
    assert (await client.post("/api/v1/auth/otp/verify", json=payload)).status_code == 200
    assert (await client.post("/api/v1/auth/otp/verify", json=payload)).status_code == 401


@pytest.mark.asyncio
async def test_refresh_replay_revokes_family(auth_client) -> None:
    client, otp_sender = auth_client
    await client.post(
        "/api/v1/auth/otp/request",
        json={"mobile_number": "+919999999999", "device_id": "phone-1"},
    )
    verified = await client.post(
        "/api/v1/auth/otp/verify",
        json={
            "mobile_number": "+919999999999",
            "code": otp_sender.last_code,
            "device_id": "phone-1",
        },
    )
    old_refresh_token = verified.json()["data"]["refresh_token"]

    first_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token, "device_id": "phone-1"},
    )
    assert first_refresh.status_code == 200

    replay = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token, "device_id": "phone-1"},
    )
    assert replay.status_code == 401


@pytest.mark.asyncio
async def test_staff_password_totp_me_and_logout(auth_client, session) -> None:
    client, _ = auth_client
    settings = get_settings()
    secret = pyotp.random_base32()
    user = User(
        user_type="STAFF",
        staff_identifier="VET-001",
        display_name="District Veterinarian",
    )
    role = Role(code="VETERINARIAN", description="Government veterinarian")
    location = Location(
        level="DISTRICT",
        code="DISTRICT-001",
        name="Test District",
        hierarchy_path="/IN/STATE-001/DISTRICT-001/",
    )
    session.add_all([user, role, location])
    await session.flush()
    session.add_all(
        [
            UserRole(user_id=user.id, role_id=role.id),
            AuthIdentity(
                user_id=user.id,
                password_hash=password_hasher.hash("correct horse battery staple"),
            ),
            MfaCredential(
                user_id=user.id,
                totp_secret_encrypted=encrypt_secret(secret, settings.mfa_encryption_key),
                recovery_code_hashes=[],
                verified_at=utc_now(),
            ),
            StaffGeographicAssignment(
                user_id=user.id,
                location_id=location.id,
                active=True,
                assigned_at=utc_now(),
            ),
        ]
    )
    await session.commit()

    login = await client.post(
        "/api/v1/auth/staff/login",
        json={
            "staff_identifier": "VET-001",
            "password": "correct horse battery staple",
        },
    )
    assert login.status_code == 200
    mfa_payload = {
        "challenge_token": login.json()["data"]["challenge_token"],
        "code": pyotp.TOTP(secret).now(),
        "device_id": "staff-phone-1",
    }
    mfa = await client.post(
        "/api/v1/auth/staff/mfa/verify",
        json=mfa_payload,
    )
    assert mfa.status_code == 200
    replayed_mfa = await client.post("/api/v1/auth/staff/mfa/verify", json=mfa_payload)
    assert replayed_mfa.status_code == 401
    tokens = mfa.json()["data"]

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["data"]["roles"] == ["VETERINARIAN"]
    assert me.json()["data"]["location_path"] == "/IN/STATE-001/DISTRICT-001/"

    logout = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert logout.status_code == 200
    assert (
        await client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": tokens["refresh_token"],
                "device_id": "staff-phone-1",
            },
        )
    ).status_code == 401


@pytest.mark.asyncio
async def test_expired_access_token_is_rejected(auth_client) -> None:
    client, _ = auth_client
    settings = get_settings()
    expired = encode_jwt(
        subject=__import__("uuid").uuid4(),
        signing_key=settings.jwt_signing_key,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        lifetime=timedelta(seconds=-1),
        purpose="access",
    )

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired}"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_inactive_account_token_is_rejected_on_protected_endpoint(
    auth_client, session
) -> None:
    client, _ = auth_client
    settings = get_settings()
    user = User(
        user_type="FARMER",
        mobile_number="+919999999977",
        display_name="Disabled Farmer",
        is_active=False,
    )
    role = Role(code="FARMER", description="Farmer")
    session.add_all([user, role])
    await session.flush()
    session.add(UserRole(user_id=user.id, role_id=role.id))
    await session.commit()
    token = encode_jwt(
        subject=user.id,
        signing_key=settings.jwt_signing_key,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        lifetime=timedelta(minutes=10),
        purpose="access",
        claims={"roles": ["FARMER"], "location_path": None},
    )

    response = await client.get("/api/v1/animals", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INACTIVE_ACCOUNT"
