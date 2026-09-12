from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    cors_origins: list[str] = Field(default_factory=list)
    database_url: SecretStr
    audit_hmac_key: SecretStr
    jwt_signing_key: SecretStr
    refresh_token_pepper: SecretStr
    otp_hmac_key: SecretStr
    mfa_encryption_key: SecretStr
    jwt_issuer: str = "bovista"
    jwt_audience: str = "bovista-api"
    access_token_minutes: int = 10
    refresh_token_days: int = 30
    otp_ttl_seconds: int = 300
    max_request_body_bytes: int = Field(default=1_048_576, ge=1024, le=10_485_760)
    otp_delivery_url: str | None = None
    otp_delivery_token: SecretStr | None = None
    mfa_issuer: str = "Bovista Government Livestock Health"
    redis_url: SecretStr = SecretStr("redis://127.0.0.1:6379/0")
    outbreak_config_version: str = "outbreak-2026.1"
    outbreak_radius_km: int = 10
    outbreak_window_days: int = 7
    outbreak_minimum_reports: int = 3
    outbreak_mortality_zscore: float = 2.0
    outbreak_frequency_ratio: float = 1.5

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        raw = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        if raw.startswith("postgres://"):
            return SecretStr(raw.replace("postgres://", "postgresql+asyncpg://", 1))
        if raw.startswith("postgresql://") and "+asyncpg" not in raw.split("://", 1)[0]:
            return SecretStr(raw.replace("postgresql://", "postgresql+asyncpg://", 1))
        return value

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if not self.is_production:
            return self
        if not self.cors_origins or "*" in self.cors_origins:
            raise ValueError("Production CORS origins must be an explicit non-empty allowlist.")
        for origin in self.cors_origins:
            parsed_origin = urlsplit(origin)
            if (
                parsed_origin.scheme != "https"
                or not parsed_origin.netloc
                or parsed_origin.path
                or parsed_origin.query
                or parsed_origin.fragment
            ):
                raise ValueError("Production CORS origins must be exact HTTPS origins.")
        database_url = self.database_url.get_secret_value()
        if not database_url.startswith("postgresql+asyncpg://"):
            raise ValueError("Production DATABASE_URL must use PostgreSQL with asyncpg.")
        redis = urlsplit(self.redis_url.get_secret_value())
        if redis.scheme not in {"redis", "rediss"} or redis.hostname in {
            None,
            "localhost",
            "127.0.0.1",
            "::1",
        }:
            raise ValueError("Production REDIS_URL must reference a non-local Redis service.")
        delivery_url = urlsplit(self.otp_delivery_url or "")
        if delivery_url.scheme != "https" or not delivery_url.netloc:
            raise ValueError("Production OTP_DELIVERY_URL must be an HTTPS endpoint.")
        if self.otp_delivery_token is None:
            raise ValueError("Production OTP_DELIVERY_TOKEN is required.")
        named_secrets = {
            "AUDIT_HMAC_KEY": self.audit_hmac_key,
            "JWT_SIGNING_KEY": self.jwt_signing_key,
            "REFRESH_TOKEN_PEPPER": self.refresh_token_pepper,
            "OTP_HMAC_KEY": self.otp_hmac_key,
            "OTP_DELIVERY_TOKEN": self.otp_delivery_token,
        }
        revealed = {name: value.get_secret_value() for name, value in named_secrets.items()}
        for name, value in revealed.items():
            if len(value.encode()) < 32 or "replace-with" in value.casefold():
                raise ValueError(f"{name} must be a non-placeholder secret of at least 32 bytes.")
        if len(set(revealed.values())) != len(revealed):
            raise ValueError("Production security secrets must be distinct.")
        try:
            Fernet(self.mfa_encryption_key.get_secret_value().encode())
        except (TypeError, ValueError) as error:
            raise ValueError("MFA_ENCRYPTION_KEY must be a valid Fernet key.") from error
        return self

    @property
    def is_production(self) -> bool:
        return self.environment.casefold() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
