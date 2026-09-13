"""Operator-only staff provisioning; credentials are entered through hidden prompts."""

import argparse
import asyncio
import getpass
from uuid import UUID

import pyotp
from sqlalchemy import select

from app.core.config import get_settings
from app.core.crypto import encrypt_secret, password_hasher
from app.db.base import utc_now
from app.db.session import async_session_factory, engine
from app.models.geography import Location, StaffGeographicAssignment
from app.models.identity import ROLE_CODES, AuthIdentity, MfaCredential, Role, User, UserRole
from app.services.trust import record_audit


async def provision(
    session, *, identifier, name, role_code, location_id, password, totp_secret, code
):
    if role_code not in ROLE_CODES or role_code == "FARMER":
        raise ValueError("A staff role is required.")
    if len(password) < 14:
        raise ValueError("Use a password of at least 14 characters.")
    if not pyotp.TOTP(totp_secret).verify(code, valid_window=1):
        raise ValueError("The authenticator code did not verify.")
    if await session.scalar(select(User.id).where(User.staff_identifier == identifier)):
        raise ValueError("That staff account already exists; it was not modified.")
    if role_code != "ADMIN" and location_id is None:
        raise ValueError("Non-admin staff require an assigned location.")
    if location_id is not None and await session.get(Location, location_id) is None:
        raise ValueError("Assigned location does not exist.")
    role = await session.scalar(select(Role).where(Role.code == role_code))
    if role is None:
        role = Role(code=role_code, description=role_code.replace("_", " ").title())
        session.add(role)
    user = User(user_type="STAFF", staff_identifier=identifier, display_name=name)
    session.add(user)
    await session.flush()
    session.add(UserRole(user_id=user.id, role_id=role.id))
    session.add(
        AuthIdentity(
            user_id=user.id,
            password_hash=password_hasher.hash(password),
            password_changed_at=utc_now(),
        )
    )
    session.add(
        MfaCredential(
            user_id=user.id,
            totp_secret_encrypted=encrypt_secret(totp_secret, get_settings().mfa_encryption_key),
            verified_at=utc_now(),
        )
    )
    if location_id:
        session.add(
            StaffGeographicAssignment(
                user_id=user.id, location_id=location_id, active=True, assigned_at=utc_now()
            )
        )
    await record_audit(
        session, None, "operator.staff.provision", "user", user.id, True, {"role": role_code}
    )
    await session.flush()
    return user.id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identifier", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", choices=[r for r in ROLE_CODES if r != "FARMER"], required=True)
    parser.add_argument("--location-id", type=UUID)
    args = parser.parse_args()
    password = getpass.getpass("New staff password (14+ characters): ")
    if password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords did not match.")
    secret = getpass.getpass(
        "Authenticator Base32 secret (already enrolled on staff device): "
    ).strip()
    code = getpass.getpass("Current authenticator code: ").strip()

    async def run():
        try:
            async with async_session_factory() as session, session.begin():
                user_id = await provision(
                    session,
                    identifier=args.identifier,
                    name=args.name,
                    role_code=args.role,
                    location_id=args.location_id,
                    password=password,
                    totp_secret=secret,
                    code=code,
                )
            print(f"Staff account created: {user_id}")
        finally:
            await engine.dispose()

    asyncio.run(run())


if __name__ == "__main__":
    main()
