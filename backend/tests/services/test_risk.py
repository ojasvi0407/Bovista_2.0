from decimal import Decimal

import pytest

from app.risk.scoring import RiskCategory, RiskFactor, RiskScorer, category_for


@pytest.mark.parametrize(
    ("value", "category"),
    [
        (0, "LOW"),
        (30, "LOW"),
        (31, "MEDIUM"),
        (60, "MEDIUM"),
        (61, "HIGH"),
        (80, "HIGH"),
        (81, "CRITICAL"),
        (100, "CRITICAL"),
    ],
)
def test_risk_boundaries(value: int, category: str) -> None:
    assert category_for(value).value == category


def test_risk_contributions_and_missing_data_are_explicit() -> None:
    decision = RiskScorer().score(
        signals={"mortality_ratio": Decimal("0.8")},
        factors=(
            RiskFactor("mortality_ratio", "report.mortality_ratio", Decimal("0.8")),
            RiskFactor("cluster", "surveillance.cluster_density", Decimal("0.3")),
        ),
        version="risk-2026.1",
    )

    assert decision.value == 64
    assert decision.category is RiskCategory.HIGH
    assert decision.missing_signals == ("surveillance.cluster_density",)
    assert decision.data_confidence == Decimal("0.5")
