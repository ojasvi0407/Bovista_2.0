import pyotp
import pytest

from app.core.config import get_settings
from app.services.auth import AuthenticationError, authenticate_staff_password, verify_staff_mfa
from scripts.provision_staff import provision


async def test_provisioned_staff_authenticates_and_mfa_limits_attempts(session):
    settings = get_settings()
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    password = "Test-only long staff password"  # noqa: S105
    user_id = await provision(
        session,
        identifier="PROVISION-TEST",
        name="Admin",
        role_code="ADMIN",
        location_id=None,
        password=password,
        totp_secret=secret,
        code=totp.now(),
    )
    await session.commit()
    challenge = await authenticate_staff_password(session, "PROVISION-TEST", password, settings)
    await session.commit()
    user, _ = await verify_staff_mfa(session, challenge, totp.now(), "test-device", settings)
    assert user.id == user_id
    await session.commit()
    challenge = await authenticate_staff_password(session, "PROVISION-TEST", password, settings)
    await session.commit()
    invalid = next(f"{i:06d}" for i in range(100) if not totp.verify(f"{i:06d}", valid_window=1))
    for _ in range(3):
        with pytest.raises(AuthenticationError):
            await verify_staff_mfa(session, challenge, invalid, "test-device", settings)
        await session.commit()
    replacement = await authenticate_staff_password(session, "PROVISION-TEST", password, settings)
    await session.commit()
    with pytest.raises(AuthenticationError):
        await verify_staff_mfa(session, challenge, totp.now(), "test-device", settings)
    for _ in range(2):
        with pytest.raises(AuthenticationError):
            await verify_staff_mfa(session, replacement, invalid, "test-device", settings)
        await session.commit()
    with pytest.raises(AuthenticationError):
        await authenticate_staff_password(session, "PROVISION-TEST", password, settings)
