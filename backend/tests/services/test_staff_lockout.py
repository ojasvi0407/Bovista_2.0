import pytest

from app.core.config import get_settings
from app.core.crypto import password_hasher
from app.models.identity import AuthIdentity, User
from app.services.auth import AuthenticationError, authenticate_staff_password


@pytest.mark.asyncio
async def test_five_failed_passwords_lock_staff_account(session) -> None:
    user = User(
        user_type="STAFF",
        staff_identifier="LOCKOUT-001",
        display_name="Lockout Test",
    )
    session.add(user)
    await session.flush()
    session.add(
        AuthIdentity(
            user_id=user.id,
            password_hash=password_hasher.hash("correct horse battery staple"),
        )
    )
    await session.flush()

    for _ in range(5):
        with pytest.raises(AuthenticationError):
            await authenticate_staff_password(
                session, "LOCKOUT-001", "incorrect password", get_settings()
            )

    with pytest.raises(AuthenticationError, match="temporarily locked"):
        await authenticate_staff_password(
            session,
            "LOCKOUT-001",
            "correct horse battery staple",
            get_settings(),
        )
