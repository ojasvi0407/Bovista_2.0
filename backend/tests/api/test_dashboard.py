from collections.abc import AsyncIterator
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from geoalchemy2.elements import WKTElement
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.crypto import encode_jwt
from app.db.base import utc_now
from app.db.rls import apply_rls
from app.db.session import get_session
from app.main import create_app
from app.models.clinical import Vaccination
from app.models.decisions import RiskRulePack, RiskScore, TriageResult, TriageRulePack
from app.models.geography import Location, StaffGeographicAssignment
from app.models.identity import Role, User, UserRole
from app.models.laboratory import LaboratorySample
from app.models.reports import Animal, DiseaseReport, Farm
from app.models.surveillance import Outbreak, VeterinaryCase


@pytest.fixture
async def dashboard_client(session) -> AsyncIterator[AsyncClient]:
    officer = User(
        user_type="STAFF",
        staff_identifier="DASHBOARD-OFFICER",
        display_name="Dashboard Officer",
    )
    inside_farmer = User(
        user_type="FARMER",
        mobile_number="+919999999953",
        display_name="Private Inside Farmer",
    )
    outside_farmer = User(
        user_type="FARMER",
        mobile_number="+919999999954",
        display_name="Private Outside Farmer",
    )
    role = Role(code="DISTRICT_OFFICER", description="District officer")
    district = Location(
        level="DISTRICT",
        code="DASHBOARD-DISTRICT",
        name="Dashboard District",
        hierarchy_path="/IN/STATE-1/DASHBOARD-DISTRICT/",
    )
    inside = Location(
        parent_id=None,
        level="VILLAGE",
        code="DASHBOARD-INSIDE",
        name="Inside Village",
        hierarchy_path="/IN/STATE-1/DASHBOARD-DISTRICT/DASHBOARD-INSIDE/",
    )
    outside = Location(
        level="VILLAGE",
        code="DASHBOARD-OUTSIDE",
        name="Outside Village",
        hierarchy_path="/IN/STATE-1/OTHER-DISTRICT/DASHBOARD-OUTSIDE/",
    )
    rule_pack = RiskRulePack(version="dashboard-risk-1", factors={}, active=True)
    triage_rule_pack = TriageRulePack(version="dashboard-triage-1", rules=[], active=True)
    session.add_all(
        [
            officer,
            inside_farmer,
            outside_farmer,
            role,
            district,
            inside,
            outside,
            rule_pack,
            triage_rule_pack,
        ]
    )
    await session.flush()
    inside.parent_id = district.id
    session.add_all(
        [
            UserRole(user_id=officer.id, role_id=role.id),
            StaffGeographicAssignment(
                user_id=officer.id,
                location_id=district.id,
                active=True,
                assigned_at=utc_now(),
            ),
        ]
    )
    inside_farm = Farm(owner_id=inside_farmer.id, location_id=inside.id, name="Private Farm")
    outside_farm = Farm(owner_id=outside_farmer.id, location_id=outside.id, name="Outside Farm")
    session.add_all([inside_farm, outside_farm])
    await session.flush()
    inside_animal = Animal(
        farm_id=inside_farm.id,
        species="CATTLE",
        tag_number="SECRET-TAG-IN",
    )
    outside_animal = Animal(
        farm_id=outside_farm.id,
        species="GOAT",
        tag_number="SECRET-TAG-OUT",
    )
    session.add_all([inside_animal, outside_animal])
    inside_report = _report(inside_farmer.id, inside_farm.id, inside, "CATTLE", 2)
    outside_report = _report(outside_farmer.id, outside_farm.id, outside, "GOAT", 4)
    session.add_all([inside_report, outside_report])
    await session.flush()
    session.add_all(
        [
            VeterinaryCase(
                disease_report_id=inside_report.id,
                status="OPEN",
                escalation_reason="High risk",
            ),
            VeterinaryCase(
                disease_report_id=outside_report.id,
                status="OPEN",
                escalation_reason="Outside risk",
            ),
            RiskScore(
                disease_report_id=inside_report.id,
                rule_pack_id=rule_pack.id,
                rule_pack_version=rule_pack.version,
                snapshot_hash=inside_report.snapshot_hash,
                value=75,
                category="HIGH",
                data_confidence=Decimal("0.8"),
                missing_signals=[],
                invoked_by_id=officer.id,
                created_at=utc_now(),
            ),
            TriageResult(
                disease_report_id=inside_report.id,
                rule_pack_id=triage_rule_pack.id,
                rule_pack_version=triage_rule_pack.version,
                snapshot_hash=inside_report.snapshot_hash,
                suspected_diseases=[{"disease_code": "FMD", "score": 0.9}],
                contributing_factors=["clinical-signs"],
                missing_fields=[],
                recommended_actions=["isolate"],
                data_confidence=Decimal("0.9"),
                disclaimer="Decision support only.",
                invoked_by_id=officer.id,
                created_at=utc_now(),
            ),
            Vaccination(
                animal_id=inside_animal.id,
                vaccine_name="FMD vaccine",
                batch_number="SAFE-BATCH-1",
                administered_on=date.today(),
                next_due_on=date.today() + timedelta(days=30),
                administered_by_id=officer.id,
            ),
            LaboratorySample(
                disease_report_id=inside_report.id,
                specimen_type="BLOOD",
                status="PROCESSING",
                created_by_id=officer.id,
            ),
            Outbreak(
                location_id=district.id,
                disease_code="FMD",
                state="DECLARED",
                config_version="dashboard-1",
                score=Decimal("80"),
                factors=[],
                cluster_geometry=WKTElement("POINT(77.1 28.6)", srid=4326),
            ),
        ]
    )
    await session.commit()
    await apply_rls(session)
    await session.commit()

    settings = get_settings()
    token = encode_jwt(
        subject=officer.id,
        signing_key=settings.jwt_signing_key,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        lifetime=timedelta(minutes=10),
        purpose="access",
        claims={"roles": ["DISTRICT_OFFICER"], "location_path": district.hierarchy_path},
    )
    application = create_app()

    async def override_session():
        yield session

    application.dependency_overrides[get_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://testserver"
    ) as client:
        client.headers["Authorization"] = f"Bearer {token}"
        yield client


@pytest.mark.asyncio
async def test_dashboard_is_scoped_aggregated_and_deidentified(dashboard_client) -> None:
    response = await dashboard_client.get(
        "/api/v1/dashboard/summary",
        params={"group_by": "species"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["totals"] == {
        "total_animals": 1,
        "active_cases": 1,
        "disease_reports": 1,
        "mortality": 2,
        "vaccination_coverage_percent": "100.00",
        "active_outbreaks": 1,
        "high_risk_locations": 1,
        "pending_laboratory_samples": 1,
    }
    assert data["groups"] == [{"key": "CATTLE", "report_count": 1, "mortality_count": 2}]
    serialized = response.text
    for private_value in (
        "Private Inside Farmer",
        "+919999999953",
        "SECRET-TAG-IN",
        "77.1",
        "28.6",
    ):
        assert private_value not in serialized


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("params", "expected_key"),
    [
        ({"group_by": "date"}, date.today().isoformat()),
        ({"group_by": "disease"}, "FMD"),
        (
            {"group_by": "location", "location_level": "DISTRICT"},
            "DASHBOARD-DISTRICT",
        ),
    ],
)
async def test_dashboard_supports_each_aggregate_dimension(
    dashboard_client, params, expected_key
) -> None:
    response = await dashboard_client.get("/api/v1/dashboard/summary", params=params)

    assert response.status_code == 200
    assert response.json()["data"]["groups"] == [
        {"key": expected_key, "report_count": 1, "mortality_count": 2}
    ]


@pytest.mark.asyncio
async def test_dashboard_filters_by_disease_and_species(dashboard_client) -> None:
    matching = await dashboard_client.get(
        "/api/v1/dashboard/summary",
        params={"group_by": "disease", "disease_code": "FMD"},
    )
    excluded = await dashboard_client.get(
        "/api/v1/dashboard/summary",
        params={"group_by": "species", "species": "GOAT"},
    )

    assert matching.status_code == 200
    assert matching.json()["data"]["totals"]["disease_reports"] == 1
    assert excluded.status_code == 200
    assert excluded.json()["data"]["totals"]["disease_reports"] == 0


@pytest.mark.asyncio
async def test_dashboard_rejects_farmer_access(dashboard_client, session) -> None:
    farmer = await session.scalar(select(User).where(User.mobile_number == "+919999999953"))
    settings = get_settings()
    token = encode_jwt(
        subject=farmer.id,
        signing_key=settings.jwt_signing_key,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        lifetime=timedelta(minutes=10),
        purpose="access",
        claims={"roles": ["DISTRICT_OFFICER"], "location_path": "/forged/"},
    )
    dashboard_client.headers["Authorization"] = f"Bearer {token}"

    response = await dashboard_client.get("/api/v1/dashboard/summary")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_dashboard_rejects_location_outside_assignment(dashboard_client, session) -> None:
    outside = await session.scalar(select(Location).where(Location.code == "DASHBOARD-OUTSIDE"))

    response = await dashboard_client.get(
        "/api/v1/dashboard/summary", params={"location_id": str(outside.id)}
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def _report(user_id, farm_id, location: Location, species: str, mortality: int):
    return DiseaseReport(
        reporter_id=user_id,
        client_generated_id=uuid4(),
        farm_id=farm_id,
        location_id=location.id,
        location_path=location.hierarchy_path,
        status="SUBMITTED",
        species=species,
        affected_count=5,
        mortality_count=mortality,
        onset_date=date.today(),
        report_geometry=WKTElement("POINT(77.1 28.6)", srid=4326),
        snapshot_hash=uuid4().hex * 2,
        submitted_at=utc_now(),
    )
