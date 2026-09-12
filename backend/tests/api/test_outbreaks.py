from datetime import timedelta
from decimal import Decimal

import pytest
from geoalchemy2.elements import WKTElement
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.crypto import encode_jwt
from app.db.session import get_session
from app.main import create_app
from app.models.geography import Location
from app.models.identity import User
from app.models.surveillance import Outbreak


def test_analysis_accepts_only_a_server_known_seed_report() -> None:
    schema = create_app().openapi()
    operation = schema["paths"]["/api/v1/outbreaks/analyze"]["post"]
    request_ref = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    request_name = request_ref.rsplit("/", 1)[-1]
    properties = schema["components"]["schemas"][request_name]["properties"]

    assert set(properties) == {"seed_report_id"}


@pytest.mark.asyncio
async def test_vet_cannot_declare_outbreak(session) -> None:
    settings = get_settings()
    vet = User(
        user_type="STAFF",
        staff_identifier="VET-OUTBREAK",
        display_name="Veterinarian",
    )
    location = Location(
        level="DISTRICT",
        code="DISTRICT-OUTBREAK",
        name="Outbreak District",
        hierarchy_path="/IN/STATE-1/DISTRICT-OUTBREAK/",
    )
    session.add_all([vet, location])
    await session.flush()
    outbreak = Outbreak(
        location_id=location.id,
        disease_code="FMD",
        state="POTENTIAL",
        config_version="outbreak-2026.1",
        score=Decimal(80),
        factors=[],
        cluster_geometry=WKTElement("POINT(77 28)", srid=4326),
    )
    session.add(outbreak)
    await session.commit()
    token = encode_jwt(
        subject=vet.id,
        signing_key=settings.jwt_signing_key,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        lifetime=timedelta(minutes=10),
        purpose="access",
        claims={"roles": ["VETERINARIAN"], "location_path": location.hierarchy_path},
    )
    application = create_app()

    async def override_session():
        yield session

    application.dependency_overrides[get_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://testserver"
    ) as client:
        response = await client.post(
            f"/api/v1/outbreaks/{outbreak.id}/declare",
            headers={
                "Authorization": f"Bearer {token}",
                "Idempotency-Key": "declare-1",
            },
            json={"reason": "Cluster reviewed"},
        )

    assert response.status_code == 403
