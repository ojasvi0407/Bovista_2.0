import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


def _settings(**overrides):
    values = {
        "environment": "production",
        "database_url": SecretStr("postgresql+asyncpg://app:pw@db/bovista"),
        "audit_hmac_key": SecretStr("audit-key-that-is-at-least-32-bytes-long"),
        "jwt_signing_key": SecretStr("jwt-key-that-is-at-least-32-bytes-long-x"),
        "refresh_token_pepper": SecretStr("refresh-pepper-at-least-32-bytes-long"),
        "otp_hmac_key": SecretStr("otp-hmac-key-at-least-32-bytes-long-x"),
        "mfa_encryption_key": SecretStr("MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="),
        "cors_origins": ["https://bovista.gov.in"],
        "redis_url": SecretStr("rediss://bovista-redis.internal:6379/0"),
        "otp_delivery_url": "https://sms.gov.in/v1/otp",
        "otp_delivery_token": SecretStr("sms-gateway-token-at-least-32-bytes-long"),
    }
    values.update(overrides)
    return Settings(**values)


def test_production_rejects_placeholder_secret() -> None:
    with pytest.raises(ValidationError):
        _settings(jwt_signing_key=SecretStr("replace-with-a-secret-of-at-least-32-bytes"))


def test_production_rejects_reused_secrets() -> None:
    shared = SecretStr("same-secret-is-long-enough-but-not-safe-123")
    with pytest.raises(ValidationError):
        _settings(jwt_signing_key=shared, otp_hmac_key=shared)


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError):
        _settings(cors_origins=["*"])


def test_production_rejects_invalid_mfa_encryption_key() -> None:
    with pytest.raises(ValidationError):
        _settings(mfa_encryption_key=SecretStr("not-a-fernet-key"))


def test_production_rejects_local_redis() -> None:
    with pytest.raises(ValidationError):
        _settings(redis_url=SecretStr("redis://127.0.0.1:6379/0"))


def test_production_rejects_non_postgres_database() -> None:
    with pytest.raises(ValidationError):
        _settings(database_url=SecretStr("sqlite+aiosqlite:///bovista.db"))


def test_production_rejects_non_https_cors_origin() -> None:
    with pytest.raises(ValidationError):
        _settings(cors_origins=["http://bovista.gov.in"])


def test_unknown_environment_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _settings(environment="prod")


def test_production_requires_otp_delivery_configuration() -> None:
    with pytest.raises(ValidationError):
        _settings(otp_delivery_url=None)


@pytest.mark.parametrize("environment", ["test", "production"])
def test_non_development_rejects_local_otp_logging(environment: str) -> None:
    with pytest.raises(ValidationError, match="Local OTP logging"):
        _settings(environment=environment, local_otp_logging=True)


def test_render_postgres_url_is_normalized_for_asyncpg() -> None:
    settings = _settings(database_url=SecretStr("postgres://app:pw@db/bovista"))

    assert settings.database_url.get_secret_value().startswith("postgresql+asyncpg://")
