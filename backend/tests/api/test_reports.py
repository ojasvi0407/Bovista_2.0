from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.crypto import encode_jwt
from app.db.rls import apply_rls
from app.db.session import get_session
from app.main import create_app
from app.models.geography import Location
from app.models.identity import Role, User, UserRole
from app.models.reports import Farm, Symptom


@pytest.fixture
async def report_client(session) -> AsyncIterator[tuple[AsyncClient, Farm]]:
    settings = get_settings()
    farmer = User(
        user_type="FARMER",
        mobile_number="+919999999992",
        display_name="Report Farmer",
    )
    role = Role(code="FARMER", description="Farmer")
    location = Location(
        level="VILLAGE",
        code="VILLAGE-1",
        name="Test Village",
        hierarchy_path="/IN/STATE-1/DISTRICT-1/BLOCK-1/VILLAGE-1/",
    )
    symptom = Symptom(code="FEVER", name="Fever", severity=3)
    session.add_all([farmer, role, location, symptom])
    await session.flush()
    session.add(UserRole(user_id=farmer.id, role_id=role.id))
    farm = Farm(owner_id=farmer.id, location_id=location.id, name="Test Farm")
    session.add(farm)
    await session.commit()
    await apply_rls(session)
    await session.commit()

    token = encode_jwt(
        subject=farmer.id,
        signing_key=settings.jwt_signing_key,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        lifetime=__import__("datetime").timedelta(minutes=10),
        purpose="access",
        claims={"roles": ["FARMER"], "location_path": None},
    )
    application = create_app()

    async def override_session():
        yield session

    application.dependency_overrides[get_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://testserver"
    ) as client:
        client.headers["Authorization"] = f"Bearer {token}"
        yield client, farm


def _report_payload(farm: Farm) -> dict[str, object]:
    return {
        "client_generated_id": str(uuid4()),
        "farm_id": str(farm.id),
        "species": "CATTLE",
        "symptoms": [{"code": "FEVER", "observed_at": None}],
        "affected_count": 3,
        "mortality_count": 1,
        "onset_date": "2026-09-10",
        "latitude": "28.6139",
        "longitude": "77.2090",
        "notes": "Reduced appetite",
    }


@pytest.mark.asyncio
async def test_duplicate_creation_returns_same_report(report_client) -> None:
    client, farm = report_client
    payload = _report_payload(farm)
    headers = {"Idempotency-Key": "phone-1:report-7"}

    first = await client.post("/api/v1/disease-reports", headers=headers, json=payload)
    second = await client.post("/api/v1/disease-reports", headers=headers, json=payload)

    assert first.status_code == second.status_code == 201
    assert first.json()["data"]["id"] == second.json()["data"]["id"]


@pytest.mark.asyncio
async def test_stale_version_returns_conflict(report_client) -> None:
    client, farm = report_client
    created = await client.post(
        "/api/v1/disease-reports",
        headers={"Idempotency-Key": "create-before-submit"},
        json=_report_payload(farm),
    )
    report_id = created.json()["data"]["id"]

    response = await client.post(
        f"/api/v1/disease-reports/{report_id}/submit",
        headers={"If-Match": '"0"', "Idempotency-Key": "submit-1"},
    )

    assert response.status_code == 409
