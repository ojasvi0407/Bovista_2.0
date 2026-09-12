from collections.abc import AsyncIterator
from datetime import date, timedelta

import pytest
from geoalchemy2.elements import WKTElement
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.crypto import encode_jwt
from app.db.base import utc_now
from app.db.session import get_session
from app.main import create_app
from app.models.geography import Location
from app.models.identity import Role, User, UserRole
from app.models.reports import DiseaseReport, Farm
from app.models.surveillance import Alert
from app.models.trust import AuditLog


@pytest.fixture
async def alert_client(session) -> AsyncIterator[tuple[AsyncClient, list[Alert]]]:
    farmer = User(
        user_type="FARMER",
        mobile_number="+919999999951",
        display_name="Alert Farmer",
    )
    other = User(
        user_type="FARMER",
        mobile_number="+919999999952",
        display_name="Other Farmer",
    )
    role = Role(code="FARMER", description="Farmer")
    location = Location(
        level="VILLAGE",
        code="ALERT-VILLAGE",
        name="Alert Village",
        hierarchy_path="/IN/STATE-1/DISTRICT-1/ALERT-VILLAGE/",
    )
    session.add_all([farmer, other, role, location])
    await session.flush()
    session.add_all(
        [
            UserRole(user_id=farmer.id, role_id=role.id),
            UserRole(user_id=other.id, role_id=role.id),
        ]
    )
    own_farm = Farm(owner_id=farmer.id, location_id=location.id, name="Own Farm")
    other_farm = Farm(owner_id=other.id, location_id=location.id, name="Other Farm")
    session.add_all([own_farm, other_farm])
    await session.flush()
    own_report = _report(farmer.id, own_farm.id, location, "CATTLE")
    other_report = _report(other.id, other_farm.id, location, "GOAT")
    session.add_all([own_report, other_report])
    await session.flush()
    alerts = [
        Alert(
            disease_report_id=own_report.id,
            recipient_id=farmer.id,
            alert_type="RISK_ESCALATION",
            severity="HIGH",
            status="ACTIVE",
            message="First own alert",
        ),
        Alert(
            disease_report_id=own_report.id,
            recipient_id=farmer.id,
            alert_type="MORTALITY_SPIKE",
            severity="CRITICAL",
            status="ACTIVE",
            message="Second own alert",
        ),
        Alert(
            disease_report_id=other_report.id,
            recipient_id=other.id,
            alert_type="RISK_ESCALATION",
            severity="HIGH",
            status="ACTIVE",
            message="Other farmer alert",
        ),
    ]
    session.add_all(alerts)
    await session.commit()

    settings = get_settings()
    token = encode_jwt(
        subject=farmer.id,
        signing_key=settings.jwt_signing_key,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        lifetime=timedelta(minutes=10),
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
        yield client, alerts


@pytest.mark.asyncio
async def test_alert_list_is_scoped_and_cursor_paginated(alert_client) -> None:
    client, alerts = alert_client

    first = await client.get("/api/v1/alerts", params={"limit": 1})

    assert first.status_code == 200
    assert len(first.json()["data"]) == 1
    assert first.json()["meta"]["next_cursor"] is not None
    second = await client.get(
        "/api/v1/alerts",
        params={"limit": 1, "cursor": first.json()["meta"]["next_cursor"]},
    )
    returned_ids = {first.json()["data"][0]["id"], second.json()["data"][0]["id"]}
    assert returned_ids == {str(alerts[0].id), str(alerts[1].id)}
    assert str(alerts[2].id) not in returned_ids


@pytest.mark.asyncio
async def test_alert_list_rejects_a_malformed_cursor(alert_client) -> None:
    client, _ = alert_client

    response = await client.get("/api/v1/alerts", params={"cursor": "not-a-cursor"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_CURSOR"


@pytest.mark.asyncio
async def test_alert_acknowledgement_is_authorized_and_audited(alert_client, session) -> None:
    client, alerts = alert_client

    acknowledged = await client.post(
        f"/api/v1/alerts/{alerts[0].id}/acknowledge",
        headers={"Idempotency-Key": "ack-alert-1"},
    )
    replay = await client.post(
        f"/api/v1/alerts/{alerts[0].id}/acknowledge",
        headers={"Idempotency-Key": "ack-alert-1"},
    )
    forbidden = await client.post(
        f"/api/v1/alerts/{alerts[2].id}/acknowledge",
        headers={"Idempotency-Key": "ack-alert-other"},
    )

    assert acknowledged.status_code == replay.status_code == 200
    assert acknowledged.json()["data"]["status"] == "ACKNOWLEDGED"
    assert acknowledged.json()["data"]["acknowledged_at"] is not None
    assert replay.json()["meta"]["idempotent_replay"] is True
    assert forbidden.status_code == 404
    assert (
        await session.scalar(
            select(func.count(AuditLog.id)).where(AuditLog.action == "alert.acknowledge")
        )
        == 1
    )


def _report(user_id, farm_id, location: Location, species: str) -> DiseaseReport:
    return DiseaseReport(
        reporter_id=user_id,
        client_generated_id=__import__("uuid").uuid4(),
        farm_id=farm_id,
        location_id=location.id,
        location_path=location.hierarchy_path,
        status="SUBMITTED",
        species=species,
        affected_count=5,
        mortality_count=1,
        onset_date=date.today(),
        report_geometry=WKTElement("POINT(77.1 28.6)", srid=4326),
        snapshot_hash="a" * 64,
        submitted_at=utc_now(),
    )
