from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter
from pydantic import Field, StringConstraints, model_validator
from sqlalchemy import select, text, update

from app.api.dependencies import CurrentPrincipalDependency, PrincipalSessionDependency
from app.api.errors import ApiError
from app.api.responses import envelope
from app.api.v1.clinical import Key, Limit
from app.db.base import utc_now
from app.models.decisions import RiskRulePack, TriageRulePack
from app.models.reports import Disease
from app.schemas.operations import Name, StrictInput
from app.services.operation_commands import changed, command, require_role, view

router = APIRouter(prefix="/rule-packs", tags=["rule governance"])
Weight = Annotated[Decimal, Field(gt=0, le=1, max_digits=7, decimal_places=6)]
Signal = Annotated[str, StringConstraints(min_length=1, max_length=60, pattern=r"^[a-z0-9_]+$")]


class DiseaseRuleInput(StrictInput):
    disease_code: str = Field(min_length=1, max_length=40)
    positive_evidence: dict[Signal, Weight] = Field(min_length=1, max_length=50)
    negative_evidence: dict[Signal, Weight] = Field(default_factory=dict, max_length=50)
    required_fields: list[Signal] = Field(default_factory=list, max_length=50)
    recommended_actions: list[Name] = Field(min_length=1, max_length=20)


class TriagePackInput(StrictInput):
    version: str = Field(min_length=1, max_length=80)
    rules: list[DiseaseRuleInput] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_diseases(self):
        codes = [rule.disease_code for rule in self.rules]
        if len(codes) != len(set(codes)):
            raise ValueError("Each disease must have one rule.")
        return self


class FactorInput(StrictInput):
    source: Name
    weight: Weight


class RiskPackInput(StrictInput):
    version: str = Field(min_length=1, max_length=80)
    factors: dict[
        Literal[
            "mortality_ratio",
            "symptom_severity",
            "vaccination_gap",
            "environmental_risk",
            "data_completeness",
            "cluster_density",
            "verification_status",
        ],
        FactorInput,
    ] = Field(min_length=1, max_length=7)

    @model_validator(mode="after")
    def normalized_weights(self):
        if sum(f.weight for f in self.factors.values()) != Decimal(1):
            raise ValueError("Risk factor weights must sum to one.")
        return self


async def publish(session, principal, model, payload):
    # Serialize publication so there is only one active pack of each kind.
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": model.__tablename__},
    )
    values = payload.model_dump(mode="json")
    if model is TriageRulePack:
        codes = {rule.disease_code for rule in payload.rules}
        registered = set(
            (
                await session.scalars(
                    select(Disease.code).where(Disease.code.in_(codes), Disease.active.is_(True))
                )
            ).all()
        )
        if codes != registered:
            raise ApiError(
                422, "INVALID_RULE_PACK", "Register active diseases before publishing their rules."
            )
    await session.execute(update(model).where(model.active.is_(True)).values(active=False))
    pack = model(**values, active=True, published_at=utc_now(), published_by_id=principal.user_id)
    session.add(pack)
    return await changed(session, principal, f"{model.__tablename__}.publish", pack)


@router.post("/triage", status_code=201)
async def publish_triage(
    payload: TriagePackInput,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, "ADMIN")
    return await command(
        session,
        principal,
        idempotency_key,
        "triage-pack.publish",
        payload.model_dump(mode="json"),
        lambda: publish(session, principal, TriageRulePack, payload),
        201,
    )


@router.post("/risk", status_code=201)
async def publish_risk(
    payload: RiskPackInput,
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    idempotency_key: Key,
):
    require_role(principal, "ADMIN")
    return await command(
        session,
        principal,
        idempotency_key,
        "risk-pack.publish",
        payload.model_dump(mode="json"),
        lambda: publish(session, principal, RiskRulePack, payload),
        201,
    )


@router.get("/{kind}")
async def list_packs(
    kind: Literal["triage", "risk"],
    principal: CurrentPrincipalDependency,
    session: PrincipalSessionDependency,
    limit: Limit = 50,
    cursor: UUID | None = None,
):
    require_role(principal, "ADMIN")
    model = TriageRulePack if kind == "triage" else RiskRulePack
    statement = select(model)
    if cursor:
        statement = statement.where(model.id < cursor)
    rows = list((await session.scalars(statement.order_by(model.id.desc()).limit(limit + 1))).all())
    return envelope(
        [view(row) for row in rows[:limit]],
        meta={"next_cursor": str(rows[limit - 1].id) if len(rows) > limit else None},
    )
