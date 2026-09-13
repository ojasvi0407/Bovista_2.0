"""Exercise migrated history triggers in a disposable transaction on an *_test database."""

import asyncio
from datetime import date
from uuid import uuid4

from geoalchemy2.elements import WKTElement
from sqlalchemy import update
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.db.rls import set_rls_context
from app.db.session import async_session_factory, engine
from app.models.clinical import Vaccination
from app.models.decisions import TriageRulePack
from app.models.geography import Location
from app.models.identity import User
from app.models.reports import Animal, Disease, DiseaseReport, Farm
from app.models.surveillance import VeterinaryCase
from app.models.trust import AuditLog
from app.schemas.operations import ReasonCommand, ResultCreate, SampleCreate
from app.services.auth import CurrentPrincipal
from app.services.laboratory import refer, transition
from app.services.trust import record_audit


async def main():
    database = make_url(get_settings().database_url.get_secret_value()).database or ""
    if not database.endswith("_test"):
        raise RuntimeError("History verification requires a disposable *_test database.")
    try:
        async with async_session_factory() as session:
            try:
                user = User(
                    user_type="FARMER",
                    display_name="History verification",
                    mobile_number="+919000000001",
                )
                location = Location(
                    level="COUNTRY", code="TEST-HISTORY", name="Test", hierarchy_path="/TEST/"
                )
                pack = TriageRulePack(version=str(uuid4()), rules=[], active=True)
                disease = Disease(code=f"TEST-{uuid4().hex[:8]}", name="Test disease")
                session.add_all([user, location, pack, disease])
                await session.flush()
                await set_rls_context(session, CurrentPrincipal(user.id, ("ADMIN",), None))
                farm = Farm(owner_id=user.id, location_id=location.id, name="Test")
                session.add(farm)
                await session.flush()
                animal = Animal(farm_id=farm.id, species="CATTLE")
                session.add(animal)
                await session.flush()
                report = DiseaseReport(
                    reporter_id=user.id,
                    client_generated_id=uuid4(),
                    farm_id=farm.id,
                    location_id=location.id,
                    location_path=location.hierarchy_path,
                    status="SUBMITTED",
                    species="CATTLE",
                    affected_count=1,
                    mortality_count=0,
                    onset_date=date.today(),
                    report_geometry=WKTElement("POINT(77 28)", srid=4326),
                )
                session.add(report)
                await session.flush()
                case = VeterinaryCase(
                    disease_report_id=report.id,
                    status="IN_REVIEW",
                    escalation_reason="Migration guard verification",
                )
                session.add(case)
                await session.flush()
                principal = CurrentPrincipal(user.id, ("ADMIN",), None)
                sample_data = await refer(
                    session,
                    principal,
                    SampleCreate(disease_report_id=report.id, specimen_type="BLOOD"),
                )
                sample_id = sample_data["id"]
                reason = ReasonCommand(reason="Verified custody")
                for action in ("collect", "receive", "start-processing"):
                    await transition(session, principal, sample_id, action, reason)
                await transition(
                    session,
                    principal,
                    sample_id,
                    "result",
                    ResultCreate(
                        disease_code="TEST",
                        outcome="NEGATIVE",
                        findings="Migration trigger verification",
                    ),
                )
                await transition(session, principal, sample_id, "review", reason)
                print("workflow_service_triggers=ok")
                vaccination = Vaccination(
                    animal_id=animal.id,
                    vaccine_name="Test",
                    batch_number="Test",
                    administered_on=date.today(),
                    administered_by_id=user.id,
                )
                session.add(vaccination)
                await session.flush()
                audit = await record_audit(
                    session, user.id, "test.history", "test", animal.id, True
                )
                for model, record_id, values in (
                    (Vaccination, vaccination.id, {"batch_number": "tampered"}),
                    (AuditLog, audit.id, {"action": "tampered"}),
                    (TriageRulePack, pack.id, {"rules": [{"tampered": True}]}),
                    (Disease, disease.id, {"name": "tampered"}),
                ):
                    try:
                        async with session.begin_nested():
                            await session.execute(
                                update(model).where(model.id == record_id).values(**values)
                            )
                    except DBAPIError:
                        print(f"{model.__tablename__}_mutation_rejected=ok")
                    else:
                        raise RuntimeError(f"{model.__tablename__} accepted a forbidden mutation")
            finally:
                await session.rollback()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
