from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.rls import set_rls_context
from app.services.auth import CurrentPrincipal

settings = get_settings()
engine = create_async_engine(settings.database_url.get_secret_value(), pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


@asynccontextmanager
async def session_for(principal: CurrentPrincipal) -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session, session.begin():
        await set_rls_context(session, principal)
        yield session
