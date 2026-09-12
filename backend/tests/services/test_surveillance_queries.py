from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from geoalchemy2.elements import WKTElement

from app.models.decisions import TriageResult, TriageRulePack
from app.models.geography import Location
from app.models.identity import User
from app.models.reports import DiseaseReport, Farm
from app.repositories.surveillance import latest_triage_diseases


@pytest.mark.asyncio
async def test_latest_triage_diseases_batches_and_uses_newest_result(session) -> None:
    user = User(
        user_type="FARMER",
        mobile_number="+919999999963",
        display_name="Triage Query Farmer",
    )
    location = Location(
        level="VILLAGE",
        code="TRIAGE-QUERY-VILLAGE",
        name="Triage Query Village",
        hierarchy_path="/IN/STATE-1/DISTRICT-1/TRIAGE-QUERY-VILLAGE/",
    )
    rule_pack = TriageRulePack(version="triage-query-1", rules=[], active=True)
    session.add_all([user, location, rule_pack])
    await session.flush()
    farm = Farm(owner_id=user.id, location_id=location.id, name="Triage Query Farm")
    session.add(farm)
    await session.flush()
    first = _report(user.id, farm.id, location, "CATTLE")
    second = _report(user.id, farm.id, location, "GOAT")
    session.add_all([first, second])
    await session.flush()
    now = datetime.now(UTC)
    session.add_all(
        [
            _triage(first.id, rule_pack.id, user.id, "FMD", "a" * 64, now - timedelta(hours=1)),
            _triage(first.id, rule_pack.id, user.id, "LSD", "b" * 64, now),
            _triage(second.id, rule_pack.id, user.id, "FMD", "c" * 64, now),
        ]
    )
    await session.flush()

    result = await latest_triage_diseases(session, [first.id, second.id])

    assert result == {first.id: "LSD", second.id: "FMD"}


def _report(user_id, farm_id, location: Location, species: str) -> DiseaseReport:
    return DiseaseReport(
        reporter_id=user_id,
        client_generated_id=uuid4(),
        farm_id=farm_id,
        location_id=location.id,
        location_path=location.hierarchy_path,
        status="SUBMITTED",
        species=species,
        affected_count=2,
        mortality_count=0,
        onset_date=date.today(),
        report_geometry=WKTElement("POINT(77.1 28.6)", srid=4326),
    )


def _triage(
    report_id,
    rule_pack_id,
    user_id,
    disease_code: str,
    snapshot_hash: str,
    created_at: datetime,
) -> TriageResult:
    return TriageResult(
        disease_report_id=report_id,
        rule_pack_id=rule_pack_id,
        rule_pack_version="triage-query-1",
        snapshot_hash=snapshot_hash,
        suspected_diseases=[{"disease_code": disease_code}],
        contributing_factors=[],
        missing_fields=[],
        recommended_actions=[],
        data_confidence=Decimal("1"),
        disclaimer="Advisory only",
        invoked_by_id=user_id,
        created_at=created_at,
    )
