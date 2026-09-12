from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum


class RiskCategory(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class RiskFactor:
    factor: str
    source: str
    weight: Decimal


@dataclass(frozen=True, slots=True)
class RiskContribution:
    factor: str
    source: str
    normalized_value: Decimal
    weight: Decimal
    points: Decimal


@dataclass(frozen=True, slots=True)
class RiskDecision:
    version: str
    value: int
    category: RiskCategory
    contributions: tuple[RiskContribution, ...]
    missing_signals: tuple[str, ...]
    data_confidence: Decimal


def category_for(value: int) -> RiskCategory:
    if not 0 <= value <= 100:
        raise ValueError("Risk value must be between 0 and 100.")
    if value <= 30:
        return RiskCategory.LOW
    if value <= 60:
        return RiskCategory.MEDIUM
    if value <= 80:
        return RiskCategory.HIGH
    return RiskCategory.CRITICAL


class RiskScorer:
    def score(
        self,
        *,
        signals: dict[str, Decimal | None],
        factors: tuple[RiskFactor, ...],
        version: str,
    ) -> RiskDecision:
        contributions: list[RiskContribution] = []
        missing: list[str] = []
        for factor in factors:
            value = signals.get(factor.factor)
            if value is None:
                missing.append(factor.source)
                continue
            normalized = max(Decimal(0), min(Decimal(1), value))
            points = normalized * factor.weight * Decimal(100)
            contributions.append(
                RiskContribution(
                    factor=factor.factor,
                    source=factor.source,
                    normalized_value=normalized,
                    weight=factor.weight,
                    points=points,
                )
            )
        raw_score = min(Decimal(100), sum((item.points for item in contributions), Decimal(0)))
        value = int(raw_score.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        confidence = (
            Decimal(0)
            if not factors
            else (Decimal(len(factors) - len(missing)) / Decimal(len(factors))).quantize(
                Decimal("0.00001")
            )
        )
        return RiskDecision(
            version=version,
            value=value,
            category=category_for(value),
            contributions=tuple(contributions),
            missing_signals=tuple(sorted(missing)),
            data_confidence=confidence,
        )
