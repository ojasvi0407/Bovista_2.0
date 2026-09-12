from app.risk.contracts import DiseaseRule, ReportSnapshot, TriageRuleSet
from app.risk.triage import ADVISORY_DISCLAIMER, RuleBasedTriageProvider


def _fmd_rules() -> TriageRuleSet:
    return TriageRuleSet(
        version="triage-2026.1",
        diseases=(
            DiseaseRule(
                disease_code="FMD",
                positive_evidence={"vesicles": 0.7, "fever": 0.3},
                negative_evidence={"vaccinated_recently": 0.2},
                required_fields=("vaccination_status",),
                recommended_actions=("isolate_affected_animals", "contact_veterinarian"),
            ),
        ),
    )


def test_triage_explains_evidence() -> None:
    snapshot = ReportSnapshot(
        snapshot_hash="snapshot-1",
        signals={
            "vesicles": True,
            "fever": True,
            "vaccinated_recently": True,
            "vaccination_status": "CURRENT",
        },
    )

    decision = RuleBasedTriageProvider().evaluate(snapshot, _fmd_rules())
    candidate = decision.suspected_diseases[0]

    assert candidate.disease_code == "FMD"
    assert "vesicles" in candidate.contributing_symptoms
    assert "vaccinated_recently" in candidate.negative_evidence
    assert decision.rule_pack_version == "triage-2026.1"
    assert decision.disclaimer == ADVISORY_DISCLAIMER


def test_missing_data_reduces_confidence() -> None:
    snapshot = ReportSnapshot(
        snapshot_hash="snapshot-2",
        signals={"vesicles": True, "fever": True},
    )

    decision = RuleBasedTriageProvider().evaluate(snapshot, _fmd_rules())

    assert decision.data_confidence < 1.0
    assert "vaccination_status" in decision.missing_fields
