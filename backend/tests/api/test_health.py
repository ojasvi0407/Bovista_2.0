from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_session
from app.main import create_app


def _app_with_healthy_database():
    application = create_app()

    class HealthySession:
        async def execute(self, statement) -> None:
            del statement

    async def override_session():
        yield HealthySession()

    application.dependency_overrides[get_session] = override_session
    return application


def test_health_uses_stable_envelope() -> None:
    response = TestClient(_app_with_healthy_database()).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "data": {"status": "healthy"},
        "meta": {"request_id": response.headers["x-request-id"]},
        "error": None,
    }


def test_security_headers_are_present() -> None:
    response = TestClient(_app_with_healthy_database()).get("/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_health_reports_database_unavailability() -> None:
    application = create_app()

    class FailingSession:
        async def execute(self, statement) -> None:
            del statement
            raise SQLAlchemyError("database unavailable")

    async def override_session():
        yield FailingSession()

    application.dependency_overrides[get_session] = override_session
    response = TestClient(application).get("/health")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
