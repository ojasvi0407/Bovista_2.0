from app.main import create_app


def test_openapi_documents_security_and_disclaimer() -> None:
    schema = create_app().openapi()

    assert "bearerAuth" in schema["components"]["securitySchemes"]
    triage = schema["paths"]["/api/v1/disease-reports/{report_id}/triage"]["post"]
    assert "Advisory only" in str(triage)
    idempotency_parameter = next(
        item for item in triage["parameters"] if item["name"] == "Idempotency-Key"
    )
    assert idempotency_parameter["schema"]["maxLength"] == 200
