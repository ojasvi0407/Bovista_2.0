from uuid import uuid4

import pytest

from app.models.geography import Location
from app.models.identity import User
from app.models.reports import Animal, Farm
from app.services.animals import AnimalAccessError, get_animal_by_id, list_animals
from app.services.auth import CurrentPrincipal


@pytest.mark.asyncio
async def test_admin_animal_list_respects_limit_and_hides_deleted(session) -> None:
    owner = User(
        user_type="FARMER",
        mobile_number="+919999999966",
        display_name="Query Farmer",
    )
    location = Location(
        level="VILLAGE",
        code="QUERY-VILLAGE",
        name="Query Village",
        hierarchy_path="/IN/QUERY/",
    )
    session.add_all([owner, location])
    await session.flush()
    farm = Farm(owner_id=owner.id, location_id=location.id, name="Query Farm")
    session.add(farm)
    await session.flush()
    session.add_all(
        [Animal(farm_id=farm.id, species="CATTLE", tag_number=f"Q-{index}") for index in range(3)]
    )
    await session.flush()
    principal = CurrentPrincipal(uuid4(), ("ADMIN",), None)

    result = await list_animals(session, principal, limit=2)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_vet_animal_reads_are_limited_to_assigned_geography(session) -> None:
    owner = User(
        user_type="FARMER",
        mobile_number="+919999999965",
        display_name="Scoped Farmer",
    )
    inside = Location(
        level="VILLAGE",
        code="QUERY-IN-SCOPE",
        name="Inside Village",
        hierarchy_path="/IN/STATE-1/DISTRICT-1/QUERY-IN-SCOPE/",
    )
    outside = Location(
        level="VILLAGE",
        code="QUERY-OUT-SCOPE",
        name="Outside Village",
        hierarchy_path="/IN/STATE-1/DISTRICT-2/QUERY-OUT-SCOPE/",
    )
    session.add_all([owner, inside, outside])
    await session.flush()
    inside_farm = Farm(owner_id=owner.id, location_id=inside.id, name="Inside Farm")
    outside_farm = Farm(owner_id=owner.id, location_id=outside.id, name="Outside Farm")
    session.add_all([inside_farm, outside_farm])
    await session.flush()
    inside_animal = Animal(farm_id=inside_farm.id, species="CATTLE", tag_number="IN")
    outside_animal = Animal(farm_id=outside_farm.id, species="CATTLE", tag_number="OUT")
    session.add_all([inside_animal, outside_animal])
    await session.flush()
    principal = CurrentPrincipal(
        uuid4(),
        ("VETERINARIAN",),
        "/IN/STATE-1/DISTRICT-1/",
    )

    result = await list_animals(session, principal, limit=50)

    assert [item["tag_number"] for item in result] == ["IN"]
    assert (await get_animal_by_id(session, principal, inside_animal.id))["tag_number"] == "IN"
    with pytest.raises(AnimalAccessError):
        await get_animal_by_id(session, principal, outside_animal.id)
