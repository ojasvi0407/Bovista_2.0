from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError
from app.core.config import Settings, get_settings
from app.db.rls import set_rls_context
from app.db.session import get_session
from app.models.geography import Location, StaffGeographicAssignment
from app.models.identity import Role, User, UserRole
from app.services.auth import AuthenticationError, CurrentPrincipal, principal_from_access_token

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="bearerAuth",
    bearerFormat="JWT",
    description="Short-lived PashuMitra access token.",
)


async def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentPrincipal:
    if credentials is None:
        raise ApiError(401, "AUTHENTICATION_REQUIRED", "A bearer token is required.")
    try:
        token_principal = await principal_from_access_token(credentials.credentials, settings)
    except AuthenticationError as error:
        raise ApiError(401, "INVALID_ACCESS_TOKEN", str(error)) from error
    user = await session.get(User, token_principal.user_id)
    if user is None or not user.is_active:
        raise ApiError(401, "INACTIVE_ACCOUNT", "The account is inactive.")
    roles = tuple(
        (
            await session.scalars(
                select(Role.code)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user.id)
                .order_by(Role.code)
            )
        ).all()
    )
    location_path = await session.scalar(
        select(Location.hierarchy_path)
        .join(
            StaffGeographicAssignment,
            StaffGeographicAssignment.location_id == Location.id,
        )
        .where(
            StaffGeographicAssignment.user_id == user.id,
            StaffGeographicAssignment.active.is_(True),
        )
    )
    return CurrentPrincipal(user_id=user.id, roles=roles, location_path=location_path)


CurrentPrincipalDependency = Annotated[CurrentPrincipal, Depends(get_current_principal)]


async def get_principal_session(
    principal: CurrentPrincipalDependency,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AsyncSession:
    await set_rls_context(session, principal)
    return session


PrincipalSessionDependency = Annotated[AsyncSession, Depends(get_principal_session)]
