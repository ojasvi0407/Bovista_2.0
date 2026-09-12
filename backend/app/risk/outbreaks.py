import math
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CandidateReport:
    report_id: UUID
    disease_code: str
    latitude: Decimal
    longitude: Decimal
    observed_at: datetime
    mortality_zscore: Decimal
    baseline_frequency_ratio: Decimal


@dataclass(frozen=True, slots=True)
class OutbreakConfig:
    version: str
    radius_km: Decimal
    window_days: int
    minimum_similar_reports: int
    mortality_zscore_threshold: Decimal
    frequency_ratio_threshold: Decimal
    weather_risk: Decimal = Decimal(0)


@dataclass(frozen=True, slots=True)
class OutbreakFactor:
    name: str
    value: Decimal
    threshold: Decimal
    matched: bool


@dataclass(frozen=True, slots=True)
class OutbreakSignal:
    detected: bool
    state: str | None
    config_version: str
    score: Decimal
    factors: tuple[OutbreakFactor, ...]
    report_ids: tuple[UUID, ...]


def distance_km(first: CandidateReport, second: CandidateReport) -> Decimal:
    lat1, lon1 = math.radians(float(first.latitude)), math.radians(float(first.longitude))
    lat2, lon2 = math.radians(float(second.latitude)), math.radians(float(second.longitude))
    delta_lat, delta_lon = lat2 - lat1, lon2 - lon1
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return Decimal(str(6371 * 2 * math.asin(math.sqrt(value))))


class OutbreakAnalyzer:
    def analyze(
        self,
        candidates: tuple[CandidateReport, ...],
        config: OutbreakConfig,
    ) -> OutbreakSignal:
        if not candidates:
            return OutbreakSignal(False, None, config.version, Decimal(0), (), ())
        same_disease = len({item.disease_code for item in candidates}) == 1
        count_matched = len(candidates) >= config.minimum_similar_reports and same_disease
        anchor = candidates[0]
        maximum_distance = max(
            (distance_km(anchor, item) for item in candidates), default=Decimal(0)
        )
        spatial_matched = maximum_distance <= config.radius_km
        observed = [item.observed_at for item in candidates]
        temporal_span = Decimal(str((max(observed) - min(observed)).total_seconds() / 86400))
        temporal_matched = temporal_span <= Decimal(config.window_days)
        mortality = max(item.mortality_zscore for item in candidates)
        frequency = max(item.baseline_frequency_ratio for item in candidates)
        factors = (
            OutbreakFactor(
                "similar_report_count",
                Decimal(len(candidates)),
                Decimal(config.minimum_similar_reports),
                count_matched,
            ),
            OutbreakFactor("spatial_cluster", maximum_distance, config.radius_km, spatial_matched),
            OutbreakFactor(
                "temporal_cluster", temporal_span, Decimal(config.window_days), temporal_matched
            ),
            OutbreakFactor(
                "mortality_anomaly",
                mortality,
                config.mortality_zscore_threshold,
                mortality >= config.mortality_zscore_threshold,
            ),
            OutbreakFactor(
                "baseline_frequency",
                frequency,
                config.frequency_ratio_threshold,
                frequency >= config.frequency_ratio_threshold,
            ),
            OutbreakFactor("weather_risk", config.weather_risk, Decimal(1), False),
        )
        detected = count_matched and spatial_matched and temporal_matched
        supporting = sum(1 for item in factors[3:5] if item.matched)
        score = Decimal(70 + supporting * 10) if detected else Decimal(0)
        return OutbreakSignal(
            detected=detected,
            state="POTENTIAL" if detected else None,
            config_version=config.version,
            score=min(Decimal(100), score),
            factors=factors,
            report_ids=tuple(item.report_id for item in candidates),
        )
