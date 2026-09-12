import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import create_app


@pytest.mark.asyncio
async def test_production_error_hides_exception() -> None:
    settings = get_settings().model_copy(update={"environment": "production"})
    application = create_app(settings)

    @application.get("/api/v1/test/internal-error")
    async def forced_error() -> None:
        raise RuntimeError("forced secret")

    async with AsyncClient(
        transport=ASGITransport(app=application, raise_app_exceptions=False),
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/v1/test/internal-error")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "Traceback" not in response.text
    assert "forced secret" not in response.text
