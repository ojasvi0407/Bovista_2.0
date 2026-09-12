import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Any
from uuid import UUID

import jwt
import phonenumbers
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.fernet import Fernet
from pydantic import SecretStr

from app.db.base import utc_now, uuid7

password_hasher = PasswordHasher()
# Used only to equalize work when a staff identifier has no stored password.
DUMMY_PASSWORD_HASH = password_hasher.hash(secrets.token_urlsafe(32))


def encrypt_secret(value: str, key: SecretStr) -> str:
    return Fernet(key.get_secret_value().encode()).encrypt(value.encode()).decode()


def decrypt_secret(value: str, key: SecretStr) -> str:
    return Fernet(key.get_secret_value().encode()).decrypt(value.encode()).decode()


def normalize_mobile_number(value: str) -> str:
    parsed = phonenumbers.parse(value, None)
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError("A valid international mobile number is required.")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def otp_digest(mobile_number: str, device_id: str, code: str, key: SecretStr) -> str:
    message = f"{mobile_number}\0{device_id}\0{code}".encode()
    return hmac.new(key.get_secret_value().encode(), message, hashlib.sha256).hexdigest()


def hash_refresh_token(raw: str, pepper: SecretStr) -> str:
    return hmac.new(pepper.get_secret_value().encode(), raw.encode(), hashlib.sha256).hexdigest()


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        return password_hasher.verify(encoded_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def encode_jwt(
    *,
    subject: UUID,
    signing_key: SecretStr,
    issuer: str,
    audience: str,
    lifetime: timedelta,
    purpose: str,
    claims: dict[str, Any] | None = None,
) -> str:
    now = utc_now()
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": now + lifetime,
        "jti": str(uuid7()),
        "typ": purpose,
    }
    payload.update(claims or {})
    return jwt.encode(payload, signing_key.get_secret_value(), algorithm="HS256")


def decode_jwt(
    token: str,
    *,
    signing_key: SecretStr,
    issuer: str,
    audience: str,
    purpose: str,
) -> dict[str, Any]:
    payload = jwt.decode(
        token,
        signing_key.get_secret_value(),
        algorithms=["HS256"],
        issuer=issuer,
        audience=audience,
    )
    if payload.get("typ") != purpose:
        raise jwt.InvalidTokenError("Unexpected token type")
    return payload
