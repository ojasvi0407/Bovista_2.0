import json

import httpx
import pytest

from app.services.auth import HttpOtpSender


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
