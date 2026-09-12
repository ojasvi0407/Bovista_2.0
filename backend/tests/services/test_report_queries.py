from datetime import date, timedelta
from uuid import uuid4

import pytest
from geoalchemy2.elements import WKTElement

from app.db.base import utc_now
from app.models.geography import Location
from app.models.identity import CaseReviewGrant, User
from app.models.reports import DiseaseReport, Farm
from app.repositories.reports import get_visible_report, list_visible_reports


@pytest.mark.asyncio
async def test_vet_report_list_is_limited_to_assigned_geography(session) -> None:
    farmer = User(
        user_type="FARMER",
        mobile_number="+919999999964",
        display_name="Report Scope Farmer",
    )
    inside = Location(
        level="VILLAGE",
        code="REPORT-IN-SCOPE",
        name="Inside Village",
        hierarchy_path="/IN/STATE-1/DISTRICT-1/REPORT-IN-SCOPE/",
    )
    outside = Location(
        level="VILLAGE",
        code="REPORT-OUT-SCOPE",
        name="Outside Village",
        hierarchy_path="/IN/STATE-1/DISTRICT-2/REPORT-OUT-SCOPE/",
    )
    session.add_all([farmer, inside, outside])
    await session.flush()
    inside_farm = Farm(owner_id=farmer.id, location_id=inside.id, name="Inside Farm")
    outside_farm = Farm(owner_id=farmer.id, location_id=outside.id, name="Outside Farm")
    session.add_all([inside_farm, outside_farm])
    await session.flush()
    inside_report = _report(farmer.id, inside_farm.id, inside, "CATTLE")
    outside_report = _report(farmer.id, outside_farm.id, outside, "GOAT")
    session.add_all([inside_report, outside_report])
    await session.flush()

    reports = await list_visible_reports(
        session,
        user_id=uuid4(),
        roles=("VETERINARIAN",),
        location_path="/IN/STATE-1/DISTRICT-1/",
    )

    assert [report.species for report in reports] == ["CATTLE"]

    officer = User(
        user_type="STAFF",
        staff_identifier="REPORT-QUERY-OFFICER",
        display_name="Review Officer",
    )
    session.add(officer)
    await session.flush()
    session.add(
        CaseReviewGrant(
            grantee_id=officer.id,
            disease_report_id=inside_report.id,
            granted_by_id=farmer.id,
            reason="Incident review",
            expires_at=utc_now() + timedelta(hours=1),
        )
    )
    await session.flush()

    granted_report = await get_visible_report(
        session,
        inside_report.id,
        user_id=officer.id,
        roles=("DISTRICT_OFFICER",),
        location_path=None,
    )

    assert granted_report is not None


def _report(farmer_id, farm_id, location: Location, species: str) -> DiseaseReport:
    return DiseaseReport(
        reporter_id=farmer_id,
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
