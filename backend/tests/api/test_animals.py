from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.crypto import encode_jwt
from app.db.rls import apply_rls
from app.db.session import get_session
from app.main import create_app
from app.models.geography import Location
from app.models.identity import Role, User, UserRole
from app.models.reports import Farm


@pytest.fixture
async def animal_client(session) -> AsyncIterator[tuple[AsyncClient, Farm]]:
    settings = get_settings()
    farmer = User(
        user_type="FARMER",
        mobile_number="+919999999981",
        display_name="Animal Farmer",
    )
    role = Role(code="FARMER", description="Farmer")
    location = Location(
        level="VILLAGE",
        code="VILLAGE-ANIMAL",
        name="Animal Village",
        hierarchy_path="/IN/STATE-1/DISTRICT-1/BLOCK-1/VILLAGE-ANIMAL/",
    )
    session.add_all([farmer, role, location])
    await session.flush()
    session.add(UserRole(user_id=farmer.id, role_id=role.id))
    farm = Farm(owner_id=farmer.id, location_id=location.id, name="Animal Farm")
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


@pytest.mark.asyncio
async def test_farmer_creates_and_lists_an_animal_on_owned_farm(animal_client) -> None:
    client, farm = animal_client
    created = await client.post(
        "/api/v1/animals",
        headers={"Idempotency-Key": "animal-create-1"},
        json={"farm_id": str(farm.id), "species": "CATTLE", "tag_number": "IN-01"},
    )

    assert created.status_code == 201
    assert created.json()["data"]["tag_number"] == "IN-01"

    listed = await client.get("/api/v1/animals")

    assert listed.status_code == 200
    assert [item["tag_number"] for item in listed.json()["data"]] == ["IN-01"]


@pytest.mark.asyncio
async def test_farmer_gets_an_owned_animal_by_id(animal_client) -> None:
    client, farm = animal_client
    created = await client.post(
        "/api/v1/animals",
        headers={"Idempotency-Key": "animal-create-detail"},
        json={"farm_id": str(farm.id), "species": "CATTLE", "tag_number": "IN-02"},
    )

    response = await client.get(f"/api/v1/animals/{created.json()['data']['id']}")

    assert response.status_code == 200
    assert response.json()["data"]["tag_number"] == "IN-02"


@pytest.mark.asyncio
async def test_farmer_updates_owned_animal_with_matching_version(animal_client) -> None:
    client, farm = animal_client
    created = await client.post(
        "/api/v1/animals",
        headers={"Idempotency-Key": "animal-create-update"},
        json={"farm_id": str(farm.id), "species": "CATTLE", "tag_number": "IN-03"},
    )
    animal = created.json()["data"]

    updated = await client.put(
        f"/api/v1/animals/{animal['id']}",
        headers={"Idempotency-Key": "animal-update-1", "If-Match": '"1"'},
        json={"tag_number": "IN-03-UPDATED"},
    )

    assert updated.status_code == 200
    assert updated.json()["data"]["tag_number"] == "IN-03-UPDATED"
    assert updated.json()["data"]["version"] == 2


@pytest.mark.asyncio
async def test_farmer_soft_deletes_owned_animal(animal_client) -> None:
    client, farm = animal_client
    created = await client.post(
        "/api/v1/animals",
        headers={"Idempotency-Key": "animal-create-delete"},
        json={"farm_id": str(farm.id), "species": "CATTLE", "tag_number": "IN-04"},
    )
    animal_id = created.json()["data"]["id"]

    deleted = await client.delete(
        f"/api/v1/animals/{animal_id}",
        headers={"Idempotency-Key": "animal-delete-1", "If-Match": '"1"'},
    )

    assert deleted.status_code == 204
    assert (await client.get(f"/api/v1/animals/{animal_id}")).status_code == 404
    assert (await client.get("/api/v1/animals")).json()["data"] == []
