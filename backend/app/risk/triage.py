from app.risk.contracts import (
    ReportSnapshot,
    SuspectedDisease,
    TriageDecision,
    TriageRuleSet,
)

ADVISORY_DISCLAIMER = "Advisory only; veterinary assessment is required for diagnosis."


class RuleBasedTriageProvider:
    def evaluate(self, snapshot: ReportSnapshot, rule_pack: TriageRuleSet) -> TriageDecision:
        candidates: list[SuspectedDisease] = []
        missing: set[str] = set()
        actions: set[str] = set()
        factors: set[str] = set()
        required: set[str] = set()

        for rule in rule_pack.diseases:
            positive_matches = tuple(
                sorted(
                    code for code in rule.positive_evidence if snapshot.signals.get(code) is True
                )
            )
            negative_matches = tuple(
                sorted(
                    code for code in rule.negative_evidence if snapshot.signals.get(code) is True
                )
            )
            positive_points = sum(rule.positive_evidence[code] for code in positive_matches)
            negative_points = sum(rule.negative_evidence[code] for code in negative_matches)
            possible = sum(rule.positive_evidence.values()) or 1.0
            normalized = max(0.0, min(1.0, (positive_points - negative_points) / possible))
            if positive_matches:
                candidates.append(
                    SuspectedDisease(
                        disease_code=rule.disease_code,
                        normalized_score=round(normalized, 6),
                        contributing_symptoms=positive_matches,
                        negative_evidence=negative_matches,
                    )
                )
                factors.update(positive_matches)
                actions.update(rule.recommended_actions)
            required.update(rule.required_fields)
            missing.update(
                field for field in rule.required_fields if snapshot.signals.get(field) is None
            )

        candidates.sort(key=lambda item: (-item.normalized_score, item.disease_code))
        confidence = 1.0 if not required else (len(required) - len(missing)) / len(required)
        return TriageDecision(
            rule_pack_version=rule_pack.version,
            suspected_diseases=tuple(candidates),
            contributing_factors=tuple(sorted(factors)),
            missing_fields=tuple(sorted(missing)),
            recommended_actions=tuple(sorted(actions)),
            data_confidence=round(confidence, 6),
            disclaimer=ADVISORY_DISCLAIMER,
        )
