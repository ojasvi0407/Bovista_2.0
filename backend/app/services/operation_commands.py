import hashlib
import json
from collections.abc import Awaitable, Callable

from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import IntegrityError

from app.api.errors import ApiError
from app.services.trust import (
    IdempotencyConflictError,
    claim_idempotency,
    enqueue_event,
    record_audit,
)


def require_role(principal, *roles):
    if not set(principal.roles).intersection(roles):
        raise ApiError(403, "FORBIDDEN", "This action is not permitted for your role.")


def view(record):
    # Only operational models without geometry or credential fields use this serializer.
    return jsonable_encoder(
        {
            c.name: getattr(record, c.name)
            for c in record.__table__.columns
            if c.name not in {"geometry", "report_geometry"}
        }
    )


async def command(
    session,
    principal,
    key: str,
    action: str,
    payload: dict,
    work: Callable[[], Awaitable[dict]],
    status: int = 200,
):
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "action": action,
                "payload": payload,
                "scope": principal.location_path,
                "roles": sorted(principal.roles),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    try:
        claim = await claim_idempotency(session, principal.user_id, key, fingerprint)
        if claim.is_replay:
            if claim.response_body is None:
                raise ApiError(409, "CONFLICT", "The original request is still being processed.")
            data = claim.response_body
        else:
            data = await work()
            await claim.store_response(status, data)
        await session.commit()
        return {"data": data, "meta": {"idempotent_replay": claim.is_replay}, "error": None}
    except IntegrityError as error:
        await session.rollback()
        raise ApiError(409, "CONFLICT", "The record conflicts with existing data.") from error
    except IdempotencyConflictError as error:
        await session.rollback()
        raise ApiError(409, "CONFLICT", str(error)) from error
    except Exception:
        await session.rollback()
        raise


async def changed(session, principal, action: str, record):
    await session.flush()
    await record_audit(session, principal.user_id, action, record.__tablename__, record.id, True)
    await enqueue_event(session, action, record.id, {"id": str(record.id)})
    return view(record)
