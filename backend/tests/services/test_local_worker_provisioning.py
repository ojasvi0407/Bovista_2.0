import importlib
import importlib.util
from uuid import UUID

from sqlalchemy import func, select

from app.models.identity import Role, User, UserRole

WORKER_ID = UUID("00000000-0000-0000-0000-000000000001")


def _provision_function():
    module_name = "scripts.provision_local_worker"
    assert (
        importlib.util.find_spec(module_name) is not None
    ), "The local worker provisioner must exist."
    return importlib.import_module(module_name).provision


async def test_local_worker_provisioner_creates_active_admin(session) -> None:
    provision = _provision_function()

    await provision(session, worker_id=WORKER_ID)

    worker = await session.get(User, WORKER_ID)
    admin_role = await session.scalar(select(Role).where(Role.code == "ADMIN"))
    assert worker is not None
    assert worker.is_active is True
    assert worker.staff_identifier == "local-outbox-worker"
    assert admin_role is not None
    assert await session.get(UserRole, (WORKER_ID, admin_role.id)) is not None


async def test_local_worker_provisioner_is_idempotent(session) -> None:
    provision = _provision_function()

    await provision(session, worker_id=WORKER_ID)
    await provision(session, worker_id=WORKER_ID)

    worker_count = await session.scalar(select(func.count()).select_from(User))
    assignment_count = await session.scalar(select(func.count()).select_from(UserRole))
    assert worker_count == 1
    assert assignment_count == 1
