from datetime import date, timedelta
from types import SimpleNamespace
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
from app.models.geography import Location, StaffGeographicAssignment
from app.models.identity import CaseReviewGrant, Role, User, UserRole
from app.models.reports import Animal, DiseaseReport, Farm
from app.models.surveillance import VeterinaryCase


@pytest.fixture
async def workflow(session):
    location = Location(level="VILLAGE", code="WF", name="Workflow", hierarchy_path="/IN/S/D/B/V/")
    outside = Location(level="VILLAGE", code="OUT", name="Outside", hierarchy_path="/IN/S/OTHER/")
    users = {}
    session.add_all([location, outside])
    await session.flush()
    for index, code in enumerate(
        [
            "FARMER",
            "VETERINARIAN",
            "PARAVET",
            "LAB_TECHNICIAN",
            "DISTRICT_OFFICER",
            "ADMIN",
        ]
    ):
        role = Role(code=code, description=code)
        user = User(
            user_type="FARMER" if code == "FARMER" else "STAFF",
            display_name=code,
            mobile_number=f"+91988888888{index}",
            staff_identifier=None if code == "FARMER" else f"WF-{code}",
        )
        session.add_all([role, user])
        await session.flush()
        session.add(UserRole(user_id=user.id, role_id=role.id))
        if code != "FARMER":
            session.add(
                StaffGeographicAssignment(
                    user_id=user.id, location_id=location.id, active=True, assigned_at=utc_now()
                )
            )
        users[code] = user
    farm = Farm(owner_id=users["FARMER"].id, location_id=location.id, name="Farm")
    session.add(farm)
    await session.flush()
    animal = Animal(farm_id=farm.id, species="CATTLE", tag_number="WF-1")
    report = DiseaseReport(
        reporter_id=users["FARMER"].id,
        client_generated_id=uuid4(),
        farm_id=farm.id,
        location_id=location.id,
        location_path=location.hierarchy_path,
        species="CATTLE",
        affected_count=1,
        mortality_count=0,
        onset_date=date.today(),
        status="SUBMITTED",
        submitted_at=utc_now(),
        report_geometry=WKTElement("POINT(77 28)", srid=4326),
    )
    session.add_all([animal, report])
    await session.flush()
    case = VeterinaryCase(disease_report_id=report.id, escalation_reason="Review")
    session.add(case)
    await session.commit()
    await apply_rls(session)
    await session.commit()
    app = create_app()

    async def override():
        yield session

    app.dependency_overrides[get_session] = override
    settings = get_settings()
    user_ids = {role: user.id for role, user in users.items()}
    references = [SimpleNamespace(id=item.id) for item in (farm, animal, report, case, outside)]

    def headers(role, key=None, version=None):
        token = encode_jwt(
            subject=user_ids[role],
            signing_key=settings.jwt_signing_key,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            lifetime=timedelta(minutes=10),
            purpose="access",
            claims={},
        )
        result = {"Authorization": f"Bearer {token}"}
        if key:
            result["Idempotency-Key"] = key
        if version:
            result["If-Match"] = f'"{version}"'
        return result

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client, headers, *references


async def test_vaccination_record_due_and_reversal(workflow):
    client, headers, _, animal, *_ = workflow
    payload = {
        "animal_id": str(animal.id),
        "vaccine_name": "FMD",
        "batch_number": "B1",
        "administered_on": str(date.today() - timedelta(days=30)),
        "next_due_on": str(date.today()),
    }
    response = await client.post(
        "/api/v1/vaccinations", headers=headers("VETERINARIAN", "v1"), json=payload
    )
    assert response.status_code == 201, response.text
    record_id = response.json()["data"]["id"]
    replay = await client.post(
        "/api/v1/vaccinations", headers=headers("VETERINARIAN", "v1"), json=payload
    )
    assert replay.json()["data"]["id"] == record_id
    due = await client.get("/api/v1/vaccinations/due", headers=headers("FARMER"))
    assert [item["id"] for item in due.json()["data"]] == [record_id]
    forbidden = await client.post(
        "/api/v1/vaccinations", headers=headers("FARMER", "v2"), json=payload
    )
    assert forbidden.status_code == 403
    reversed_record = await client.post(
        f"/api/v1/vaccinations/{record_id}/reverse",
        headers=headers("VETERINARIAN", "reverse1"),
        json={"reason": "Incorrect batch recorded"},
    )
    assert reversed_record.status_code == 200, reversed_record.text
    assert (await client.get("/api/v1/vaccinations/due", headers=headers("FARMER"))).json()[
        "data"
    ] == []


async def test_treatment_policy_and_validation(workflow):
    client, headers, _, animal, _, case, _ = workflow
    payload = {
        "animal_id": str(animal.id),
        "case_id": str(case.id),
        "medicine_name": "Prescribed medicine",
        "dosage": "2.5",
        "dosage_unit": "ml",
        "duration_days": 3,
        "administered_on": str(date.today()),
    }
    assert (
        await client.post("/api/v1/treatments", headers=headers("FARMER", "t1"), json=payload)
    ).status_code == 403
    response = await client.post(
        "/api/v1/treatments", headers=headers("VETERINARIAN", "t2"), json=payload
    )
    assert response.status_code == 201, response.text
    assert (
        await client.post(
            "/api/v1/treatments",
            headers=headers("VETERINARIAN", "t3"),
            json={**payload, "dosage": "-1"},
        )
    ).status_code == 422


async def test_lab_state_machine_roles_and_alert(workflow):
    client, headers, _, _, report, case, _ = workflow
    started = await client.post(
        f"/api/v1/cases/{case.id}/review",
        headers=headers("VETERINARIAN", "case-before-lab"),
        json={"reason": "Begin clinical review"},
    )
    assert started.status_code == 200, started.text
    created = await client.post(
        "/api/v1/lab/samples",
        headers=headers("VETERINARIAN", "l1"),
        json={"disease_report_id": str(report.id), "specimen_type": "BLOOD"},
    )
    assert created.status_code == 201, created.text
    sample_id = created.json()["data"]["id"]
    result = {
        "disease_code": "FMD",
        "outcome": "POSITIVE",
        "findings": "Validated laboratory findings",
    }
    early = await client.post(
        f"/api/v1/lab/samples/{sample_id}/result",
        headers=headers("LAB_TECHNICIAN", "early"),
        json=result,
    )
    assert early.status_code == 409, early.text
    for action, role in [
        ("collect", "PARAVET"),
        ("receive", "LAB_TECHNICIAN"),
        ("start-processing", "LAB_TECHNICIAN"),
    ]:
        response = await client.post(
            f"/api/v1/lab/samples/{sample_id}/{action}",
            headers=headers(role, action),
            json={"reason": "Chain of custody verified"},
        )
        assert response.status_code == 200, response.text
    assert (
        await client.post(
            f"/api/v1/lab/samples/{sample_id}/result",
            headers=headers("FARMER", "bad-result"),
            json=result,
        )
    ).status_code == 403
    published = await client.post(
        f"/api/v1/lab/samples/{sample_id}/result",
        headers=headers("LAB_TECHNICIAN", "result"),
        json=result,
    )
    assert published.status_code == 201, published.text
    alerts = await client.get("/api/v1/alerts", headers=headers("FARMER"))
    assert any(item["alert_type"] == "LAB_RESULT" for item in alerts.json()["data"])
    reviewed = await client.post(
        f"/api/v1/lab/samples/{sample_id}/review",
        headers=headers("VETERINARIAN", "review"),
        json={"reason": "Reviewed by vet"},
    )
    assert reviewed.status_code == 200, reviewed.text


async def test_district_case_grant_controls_case_and_lab_reads(workflow, session):
    client, headers, _, _, report, case, _ = workflow
    assert (
        await client.get(f"/api/v1/cases/{case.id}", headers=headers("DISTRICT_OFFICER"))
    ).status_code == 404
    reviewed = await client.post(
        f"/api/v1/cases/{case.id}/review",
        headers=headers("VETERINARIAN", "grant-case-review"),
        json={"reason": "Begin review for referral"},
    )
    assert reviewed.status_code == 200, reviewed.text
    sample_response = await client.post(
        "/api/v1/lab/samples",
        headers=headers("VETERINARIAN", "grant-lab-refer"),
        json={"disease_report_id": str(report.id), "specimen_type": "SERUM"},
    )
    assert sample_response.status_code == 201, sample_response.text
    sample_id = sample_response.json()["data"]["id"]
    district = await session.scalar(
        select(User).where(User.staff_identifier == "WF-DISTRICT_OFFICER")
    )
    grant = CaseReviewGrant(
        grantee_id=district.id,
        disease_report_id=report.id,
        granted_by_id=district.id,
        reason="Time-bound investigation",
        expires_at=utc_now() + timedelta(hours=1),
    )
    session.add(grant)
    await session.commit()
    assert (
        await client.get(f"/api/v1/cases/{case.id}", headers=headers("DISTRICT_OFFICER"))
    ).status_code == 200
    assert (
        await client.get(f"/api/v1/lab/samples/{sample_id}", headers=headers("DISTRICT_OFFICER"))
    ).status_code == 200
    grant.revoked_at = utc_now()
    await session.commit()
    assert (
        await client.get(f"/api/v1/cases/{case.id}", headers=headers("DISTRICT_OFFICER"))
    ).status_code == 404


async def test_farm_herd_crud_and_stale_version(workflow):
    client, headers, farm, *_ = workflow
    response = await client.post(
        "/api/v1/herds",
        headers=headers("FARMER", "h1"),
        json={"farm_id": str(farm.id), "name": "Herd", "species": "CATTLE", "animal_count": 2},
    )
    assert response.status_code == 201, response.text
    herd_id = response.json()["data"]["id"]
    updated = await client.put(
        f"/api/v1/herds/{herd_id}", headers=headers("FARMER", "h2", 1), json={"name": "Renamed"}
    )
    assert updated.status_code == 200, updated.text
    assert (
        await client.put(
            f"/api/v1/herds/{herd_id}", headers=headers("FARMER", "h3", 1), json={"name": "Stale"}
        )
    ).status_code == 409
    assert (
        await client.delete(f"/api/v1/herds/{herd_id}", headers=headers("FARMER", "h4", 2))
    ).status_code == 204
    assert (
        await client.get(f"/api/v1/herds/{herd_id}", headers=headers("FARMER"))
    ).status_code == 404
    assert (await client.get("/api/v1/farms", headers=headers("FARMER"))).status_code == 200


async def test_case_workflow_and_role_checks(workflow):
    client, headers, _, _, _, case, _ = workflow
    endpoint = f"/api/v1/cases/{case.id}"
    reason = {"reason": "Clinical review completed"}
    assert (
        await client.post(endpoint + "/review", headers=headers("FARMER", "c0"), json=reason)
    ).status_code == 403
    early = await client.post(
        endpoint + "/close", headers=headers("VETERINARIAN", "c1"), json=reason
    )
    assert early.status_code == 409
    for action in ("review", "refer", "resume", "close"):
        response = await client.post(
            endpoint + "/" + action, headers=headers("VETERINARIAN", f"case-{action}"), json=reason
        )
        assert response.status_code == 200, response.text
    history = await client.get(endpoint + "/history", headers=headers("VETERINARIAN"))
    assert len(history.json()["data"]) == 4
    assert (await client.get(endpoint, headers=headers("FARMER"))).json()["data"][
        "status"
    ] == "CLOSED"


async def test_reassigned_staff_cannot_read_or_replay_clinical_records(workflow, session):
    from sqlalchemy import select, update

    client, headers, _, animal, _, _, outside = workflow
    payload = {
        "animal_id": str(animal.id),
        "vaccine_name": "FMD",
        "batch_number": "SCOPE",
        "administered_on": str(date.today()),
    }
    created = await client.post(
        "/api/v1/vaccinations", headers=headers("VETERINARIAN", "scope1"), json=payload
    )
    assert created.status_code == 201
    record_id = created.json()["data"]["id"]
    vet_id = await session.scalar(select(User.id).where(User.staff_identifier == "WF-VETERINARIAN"))
    await session.execute(
        update(StaffGeographicAssignment)
        .where(StaffGeographicAssignment.user_id == vet_id)
        .values(location_id=outside.id)
    )
    await session.commit()
    assert (
        await client.get(f"/api/v1/vaccinations/{record_id}", headers=headers("VETERINARIAN"))
    ).status_code == 404
    replay = await client.post(
        "/api/v1/vaccinations", headers=headers("VETERINARIAN", "scope1"), json=payload
    )
    assert replay.status_code == 409


async def test_future_vaccination_excluded_from_due_list(workflow):
    client, headers, _, animal, *_ = workflow
    response = await client.post(
        "/api/v1/vaccinations",
        headers=headers("PARAVET", "future-due"),
        json={
            "animal_id": str(animal.id),
            "vaccine_name": "FMD",
            "batch_number": "FUTURE",
            "administered_on": str(date.today()),
            "next_due_on": str(date.today() + timedelta(days=30)),
        },
    )
    assert response.status_code == 201, response.text
    assert (await client.get("/api/v1/vaccinations/due", headers=headers("FARMER"))).json()[
        "data"
    ] == []


async def test_farmer_cannot_insert_vaccination_through_database(workflow, session):
    from sqlalchemy import select
    from sqlalchemy.exc import DBAPIError

    from app.db.rls import set_rls_context
    from app.models.clinical import Vaccination
    from app.services.auth import CurrentPrincipal

    _, _, _, animal, *_ = workflow
    farmer_id = await session.scalar(select(User.id).where(User.user_type == "FARMER"))
    await set_rls_context(session, CurrentPrincipal(farmer_id, ("FARMER",), None))
    session.add(
        Vaccination(
            animal_id=animal.id,
            vaccine_name="FMD",
            batch_number="BYPASS",
            administered_on=date.today(),
            administered_by_id=farmer_id,
        )
    )
    with pytest.raises(DBAPIError):
        await session.flush()
    await session.rollback()


async def test_database_rejects_farmer_case_update_and_lab_referral(workflow, session):
    from sqlalchemy import update
    from sqlalchemy.exc import DBAPIError

    from app.db.rls import set_rls_context
    from app.models.laboratory import LaboratorySample
    from app.services.auth import CurrentPrincipal

    _, _, _, _, report, case, _ = workflow
    farmer = await session.scalar(select(User).where(User.user_type == "FARMER"))
    await set_rls_context(session, CurrentPrincipal(farmer.id, ("FARMER",), None))
    changed_case = await session.execute(
        update(VeterinaryCase).where(VeterinaryCase.id == case.id).values(status="IN_REVIEW")
    )
    assert changed_case.rowcount == 0
    await session.rollback()

    lab_user = await session.scalar(
        select(User).where(User.staff_identifier == "WF-LAB_TECHNICIAN")
    )
    location = await session.scalar(select(Location).where(Location.code == "WF"))
    await set_rls_context(
        session, CurrentPrincipal(lab_user.id, ("LAB_TECHNICIAN",), location.hierarchy_path)
    )
    session.add(
        LaboratorySample(
            disease_report_id=report.id,
            specimen_type="BLOOD",
            created_by_id=lab_user.id,
        )
    )
    with pytest.raises(DBAPIError):
        await session.flush()
    await session.rollback()


async def test_farm_creation_and_parent_archive_guard(workflow, session):
    from sqlalchemy import select

    client, headers, farm, *_ = workflow
    location_id = await session.scalar(select(Location.id).where(Location.code == "WF"))
    created = await client.post(
        "/api/v1/farms",
        headers=headers("FARMER", "farm-create"),
        json={"location_id": str(location_id), "name": "New farm"},
    )
    assert created.status_code == 201, created.text
    new_id = created.json()["data"]["id"]
    assert (
        await client.delete(f"/api/v1/farms/{new_id}", headers=headers("FARMER", "farm-delete", 1))
    ).status_code == 204
    assert (
        await client.delete(f"/api/v1/farms/{farm.id}", headers=headers("FARMER", "farm-active", 1))
    ).status_code == 409


async def test_reference_data_and_rule_publication(workflow):
    client, headers, *_ = workflow
    disease = {"code": "FMD", "name": "Foot and mouth disease"}
    assert (
        await client.post("/api/v1/diseases", headers=headers("FARMER", "ref-denied"), json=disease)
    ).status_code == 403
    assert (
        await client.post("/api/v1/diseases", headers=headers("ADMIN", "ref-disease"), json=disease)
    ).status_code == 201
    revised = await client.post(
        "/api/v1/diseases/FMD/versions",
        headers=headers("ADMIN", "ref-disease-v2"),
        json={**disease, "name": "Foot-and-mouth disease"},
    )
    assert revised.status_code == 201, revised.text
    assert revised.json()["data"]["revision"] == 2
    active_diseases = await client.get("/api/v1/diseases", headers=headers("ADMIN"))
    assert [(item["code"], item["revision"]) for item in active_diseases.json()["data"]] == [
        ("FMD", 2)
    ]
    triage = {
        "version": "test-v1",
        "rules": [
            {
                "disease_code": "FMD",
                "positive_evidence": {"fever": "1"},
                "recommended_actions": ["Veterinary examination"],
            }
        ],
    }
    published = await client.post(
        "/api/v1/rule-packs/triage", headers=headers("ADMIN", "publish1"), json=triage
    )
    assert published.status_code == 201, published.text
    second = await client.post(
        "/api/v1/rule-packs/triage",
        headers=headers("ADMIN", "publish2"),
        json={**triage, "version": "test-v2"},
    )
    assert second.status_code == 201, second.text
    versions = await client.get("/api/v1/rule-packs/triage", headers=headers("ADMIN"))
    assert sum(item["active"] for item in versions.json()["data"]) == 1
    invalid_risk = await client.post(
        "/api/v1/rule-packs/risk",
        headers=headers("ADMIN", "invalid-risk"),
        json={
            "version": "bad",
            "factors": {"mortality_ratio": {"source": "clinical", "weight": "0.4"}},
        },
    )
    assert invalid_risk.status_code == 422


async def test_submitted_report_cannot_be_edited_or_archived(workflow):
    client, headers, _, _, report, *_ = workflow
    updated = await client.put(
        f"/api/v1/disease-reports/{report.id}",
        headers=headers("FARMER", "edit-frozen", 1),
        json={"affected_count": 2, "mortality_count": 0, "onset_date": str(date.today())},
    )
    assert updated.status_code == 409
    archived = await client.delete(
        f"/api/v1/disease-reports/{report.id}", headers=headers("FARMER", "archive-frozen", 1)
    )
    assert archived.status_code == 409


async def test_new_vaccine_dose_supersedes_old_due_reminder(workflow):
    client, headers, _, animal, *_ = workflow
    for key, administered, due in (
        ("old", date.today() - timedelta(days=60), date.today() - timedelta(days=30)),
        ("new", date.today(), date.today() + timedelta(days=30)),
    ):
        response = await client.post(
            "/api/v1/vaccinations",
            headers=headers("VETERINARIAN", key),
            json={
                "animal_id": str(animal.id),
                "vaccine_name": "FMD",
                "batch_number": key,
                "administered_on": str(administered),
                "next_due_on": str(due),
            },
        )
        assert response.status_code == 201, response.text
    assert (await client.get("/api/v1/vaccinations/due", headers=headers("FARMER"))).json()[
        "data"
    ] == []


async def test_animals_use_cursor_pagination(workflow):
    client, headers, farm, *_ = workflow
    created = await client.post(
        "/api/v1/animals",
        headers=headers("FARMER", "page-animal"),
        json={"farm_id": str(farm.id), "species": "CATTLE"},
    )
    assert created.status_code == 201
    first = await client.get("/api/v1/animals?limit=1", headers=headers("FARMER"))
    cursor = first.json()["meta"]["next_cursor"]
    assert cursor is not None
    second = await client.get(
        "/api/v1/animals", headers=headers("FARMER"), params={"limit": 1, "cursor": cursor}
    )
    assert len(second.json()["data"]) == 1
    assert first.json()["data"][0]["id"] != second.json()["data"][0]["id"]
    assert second.json()["meta"]["next_cursor"] is None
