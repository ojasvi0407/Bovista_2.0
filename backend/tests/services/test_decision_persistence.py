from datetime import date
from uuid import uuid4

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select

from app.db.base import utc_now
from app.models.decisions import RiskRulePack
from app.models.geography import Location
from app.models.identity import User
from app.models.reports import DiseaseReport, Farm
from app.models.surveillance import Alert, VeterinaryCase
from app.services.auth import CurrentPrincipal
from app.services.decisions import DecisionService


@pytest.mark.asyncio
async def test_high_risk_opens_case_and_alert(session) -> None:
    farmer = User(user_type="FARMER", mobile_number="+919999999993", display_name="Farmer")
    location = Location(
        level="DISTRICT",
        code="DISTRICT-RISK",
        name="Risk District",
        hierarchy_path="/IN/STATE-1/DISTRICT-RISK/",
    )
    rules = RiskRulePack(
        version="risk-2026.1",
        active=True,
        published_at=utc_now(),
        factors={
            "mortality_ratio": {"source": "report.mortality_ratio", "weight": "0.8"},
            "cluster_density": {
                "source": "surveillance.cluster_density",
                "weight": "0.2",
            },
        },
    )
    session.add_all([farmer, location, rules])
    await session.flush()
    farm = Farm(owner_id=farmer.id, location_id=location.id, name="Risk Farm")
    session.add(farm)
    await session.flush()
    report = DiseaseReport(
        reporter_id=farmer.id,
        client_generated_id=uuid4(),
        farm_id=farm.id,
        location_id=location.id,
        location_path=location.hierarchy_path,
        status="SUBMITTED",
        species="CATTLE",
        affected_count=10,
        mortality_count=8,
        onset_date=date.today(),
        report_geometry=WKTElement("POINT(77 28)", srid=4326),
        snapshot_hash="a" * 64,
        submitted_at=utc_now(),
    )
    session.add(report)
    await session.flush()

    decision = await DecisionService(session).score_risk(
        report.id,
        CurrentPrincipal(farmer.id, ("FARMER",), None),
    )
    await session.commit()

    assert decision.value == 64
    assert decision.category == "HIGH"
    assert (
        await session.scalar(
            select(func.count())
            .select_from(VeterinaryCase)
            .where(VeterinaryCase.disease_report_id == report.id)
        )
        == 1
    )
    assert (
        await session.scalar(
            select(func.count()).select_from(Alert).where(Alert.disease_report_id == report.id)
        )
        == 1
    )
