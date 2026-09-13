import json
import logging
from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr

from app.api.v1.auth import MissingOtpSender, _otp_sender
from app.core.config import Settings
from app.services import auth as auth_service
from app.services.auth import HttpOtpSender


def _development_settings(*, local_otp_logging: bool) -> Settings:
    return Settings(
        environment="development",
        database_url=SecretStr("postgresql+asyncpg://app:pw@db/bovista"),
        audit_hmac_key=SecretStr("audit-key"),
        jwt_signing_key=SecretStr("jwt-key"),
        refresh_token_pepper=SecretStr("refresh-pepper"),
        otp_hmac_key=SecretStr("otp-key"),
        mfa_encryption_key=SecretStr("MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="),
        local_otp_logging=local_otp_logging,
    )


@pytest.mark.asyncio
async def test_log_otp_sender_emits_structured_local_message(caplog) -> None:
    assert hasattr(auth_service, "LogOtpSender")
    sender = auth_service.LogOtpSender()

    with caplog.at_level(logging.WARNING):
        await sender.send("+919999999999", "123456")

    assert "local_development_otp mobile=+919999999999 code=123456" in caplog.text


def test_otp_sender_selects_logging_only_when_explicitly_enabled() -> None:
    enabled_request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    disabled_request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))

    enabled = _otp_sender(enabled_request, _development_settings(local_otp_logging=True))
    disabled = _otp_sender(disabled_request, _development_settings(local_otp_logging=False))

    assert hasattr(auth_service, "LogOtpSender")
    assert isinstance(enabled, auth_service.LogOtpSender)
    assert enabled_request.app.state.otp_sender is enabled
    assert isinstance(disabled, MissingOtpSender)


@pytest.mark.asyncio
async def test_http_otp_sender_uses_authenticated_json_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer gateway-token"
        assert json.loads(request.content) == {
            "mobile_number": "+919999999999",
            "code": "123456",
        }
        return httpx.Response(202)

    sender = HttpOtpSender("https://sms.gov.in/v1/otp", "gateway-token")
    await sender.client.aclose()
    sender.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        await sender.send("+919999999999", "123456")
    finally:
        await sender.aclose()
