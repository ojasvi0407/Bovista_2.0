from app.main import create_app


def test_decision_routes_are_exposed() -> None:
    schema = create_app().openapi()

    assert "/api/v1/disease-reports/{report_id}/triage" in schema["paths"]
    assert "/api/v1/disease-reports/{report_id}/risk-score" in schema["paths"]
