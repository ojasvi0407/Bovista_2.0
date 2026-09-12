from fastapi.testclient import TestClient

from app.main import create_app


def test_request_validation_uses_stable_error_envelope() -> None:
    response = TestClient(create_app()).post("/api/v1/auth/otp/request", json={})

    assert response.status_code == 422
    assert response.json()["data"] is None
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["meta"]["request_id"] == response.headers["x-request-id"]


def test_oversized_client_request_id_is_replaced() -> None:
    response = TestClient(create_app()).get("/health", headers={"x-request-id": "x" * 500})

    assert response.status_code == 200
    assert response.headers["x-request-id"] != "x" * 500
    assert len(response.headers["x-request-id"]) <= 64


def test_unknown_route_uses_stable_error_envelope() -> None:
    response = TestClient(create_app()).get("/api/v1/not-a-route")

    assert response.status_code == 404
    assert response.json()["data"] is None
    assert response.json()["error"] == {
        "code": "NOT_FOUND",
        "message": "The requested resource was not found.",
    }


def test_declared_oversized_request_body_is_rejected() -> None:
    response = TestClient(create_app()).post(
        "/api/v1/auth/otp/request",
        headers={"Content-Length": str(1_048_577)},
        content=b"{}",
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"
