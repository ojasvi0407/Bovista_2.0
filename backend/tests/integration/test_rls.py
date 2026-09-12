from datetime import date
from uuid import uuid4

import pytest
from geoalchemy2.elements import WKTElement

from app.db.rls import apply_rls, remove_rls, set_rls_context
from app.models.geography import Location
from app.models.identity import User
from app.models.reports import DiseaseReport, Farm, ReportContextSnapshot
from app.services.auth import CurrentPrincipal


@pytest.mark.asyncio
async def test_rls_hides_out_of_scope_report(session) -> None:
    farmer = User(
        user_type="FARMER",
        mobile_number="+919999999991",
        display_name="Farmer",
    )
    vet_id = uuid4()
    location = Location(
        level="DISTRICT",
        code="DISTRICT-2",
        name="Other District",
        hierarchy_path="/IN/STATE-1/DISTRICT-2/",
    )
    session.add_all([farmer, location])
    await session.flush()
    farm = Farm(owner_id=farmer.id, location_id=location.id, name="Other Farm")
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
        affected_count=2,
        mortality_count=0,
        onset_date=date.today(),
        report_geometry=WKTElement("POINT(77.1 28.6)", srid=4326),
    )
    session.add(report)
    await session.flush()
    context = ReportContextSnapshot(
        disease_report_id=report.id,
        vaccination={"status": "CURRENT"},
    )
    session.add(context)
    await session.commit()
    await apply_rls(session)
    await session.commit()
    report_id = report.id
    farm_id = farm.id
    context_id = context.id
    session.expunge_all()

    try:
        await set_rls_context(
            session,
            CurrentPrincipal(
                user_id=vet_id,
                roles=("VETERINARIAN",),
                location_path="/IN/STATE-1/DISTRICT-1/",
            ),
        )
        assert await session.get(DiseaseReport, report_id) is None
        assert await session.get(Farm, farm_id) is None
        assert await session.get(ReportContextSnapshot, context_id) is None
    finally:
        await session.rollback()
        await remove_rls(session)
        await session.commit()
