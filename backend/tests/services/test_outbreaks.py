from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from app.models.geography import Location
from app.models.identity import User
from app.models.surveillance import Outbreak
from app.models.trust import IdempotencyReceipt
from app.risk.outbreaks import CandidateReport, OutbreakAnalyzer, OutbreakConfig
from app.services.auth import CurrentPrincipal
from app.services.authorization import ForbiddenError
from app.services.outbreaks import authorize_outbreak_transition, transition_outbreak


def _config(*, weather_risk: Decimal = Decimal("0")) -> OutbreakConfig:
    return OutbreakConfig(
        version="outbreak-2026.1",
        radius_km=Decimal("10"),
        window_days=7,
        minimum_similar_reports=3,
        mortality_zscore_threshold=Decimal("2"),
        frequency_ratio_threshold=Decimal("1.5"),
        weather_risk=weather_risk,
    )


def _candidate(offset: int) -> CandidateReport:
    return CandidateReport(
        report_id=uuid4(),
        disease_code="FMD",
        latitude=Decimal("28.61") + Decimal(offset) / Decimal("1000"),
        longitude=Decimal("77.20") + Decimal(offset) / Decimal("1000"),
        observed_at=datetime.now(UTC) - timedelta(days=offset),
        mortality_zscore=Decimal("2.4"),
        baseline_frequency_ratio=Decimal("1.8"),
    )


def test_cluster_creates_potential_signal() -> None:
    signal = OutbreakAnalyzer().analyze((_candidate(0), _candidate(1), _candidate(2)), _config())

    assert signal.detected is True
    assert signal.state == "POTENTIAL"
    assert {factor.name for factor in signal.factors} >= {
        "spatial_cluster",
        "temporal_cluster",
    }


def test_weather_alone_never_creates_outbreak() -> None:
    signal = OutbreakAnalyzer().analyze((_candidate(0),), _config(weather_risk=Decimal("1")))

    assert signal.detected is False


def test_vet_cannot_declare_outbreak() -> None:
    principal = CurrentPrincipal(
        user_id=uuid4(),
        roles=("VETERINARIAN",),
        location_path="/IN/STATE-1/DISTRICT-1/",
    )

    try:
        authorize_outbreak_transition(principal, "/IN/STATE-1/DISTRICT-1/")
    except ForbiddenError:
        pass
    else:
        raise AssertionError("Veterinarians must not declare outbreaks")


@pytest.mark.asyncio
async def test_long_outbreak_reason_uses_bounded_idempotency_hash(session) -> None:
    officer = User(
        user_type="STAFF",
        staff_identifier="DISTRICT-OFFICER-LONG-REASON",
        display_name="District Officer",
    )
    location = Location(
        level="DISTRICT",
        code="DISTRICT-LONG-REASON",
        name="Long Reason District",
        hierarchy_path="/IN/STATE-1/DISTRICT-LONG-REASON/",
    )
    session.add_all([officer, location])
    await session.flush()
    outbreak = Outbreak(
        location_id=location.id,
        disease_code="FMD",
        state="POTENTIAL",
        config_version="outbreak-2026.1",
        score=Decimal("80"),
        factors=[],
        cluster_geometry=WKTElement("POINT(77 28)", srid=4326),
    )
    session.add(outbreak)
    await session.flush()

    await transition_outbreak(
        session,
        outbreak_id=outbreak.id,
        target_state="DECLARED",
        reason="Reviewed evidence. " * 40,
        principal=CurrentPrincipal(
            officer.id,
            ("DISTRICT_OFFICER",),
            location.hierarchy_path,
        ),
        idempotency_key="long-reason",
    )

    receipt = await session.scalar(select(IdempotencyReceipt))
    assert receipt is not None
    assert len(receipt.request_hash) == 64
