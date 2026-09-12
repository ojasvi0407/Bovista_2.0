from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ReportSnapshot:
    snapshot_hash: str
    signals: dict[str, bool | str | int | float | None]


@dataclass(frozen=True, slots=True)
class DiseaseRule:
    disease_code: str
    positive_evidence: dict[str, float]
    negative_evidence: dict[str, float]
    required_fields: tuple[str, ...]
    recommended_actions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TriageRuleSet:
    version: str
    diseases: tuple[DiseaseRule, ...]


@dataclass(frozen=True, slots=True)
class SuspectedDisease:
    disease_code: str
    normalized_score: float
    contributing_symptoms: tuple[str, ...]
    negative_evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TriageDecision:
    rule_pack_version: str
    suspected_diseases: tuple[SuspectedDisease, ...]
    contributing_factors: tuple[str, ...]
    missing_fields: tuple[str, ...]
    recommended_actions: tuple[str, ...]
    data_confidence: float
    disclaimer: str


class TriageProvider(Protocol):
    def evaluate(self, snapshot: ReportSnapshot, rule_pack: TriageRuleSet) -> TriageDecision: ...
