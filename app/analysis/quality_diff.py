"""Before/after quality comparison helpers."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from app.analysis.quality_report import QualityReport


@dataclass(frozen=True)
class QualityDeltaReport:
    source_before: str
    source_after: str
    delta_true_peak_db: float
    delta_loudness_db: float
    delta_crest_factor_db: float
    delta_dynamic_range_db: float
    clipping_removed: bool
    recommendations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def compare_quality_reports(before: QualityReport, after: QualityReport) -> QualityDeltaReport:
    delta_true_peak = after.true_peak_dbfs - before.true_peak_dbfs
    delta_loudness = after.loudness_estimate_dbfs - before.loudness_estimate_dbfs
    delta_crest = after.crest_factor_db - before.crest_factor_db
    delta_dynamic_range = after.dynamic_range_db - before.dynamic_range_db
    clipping_removed = before.clipping and not after.clipping

    recommendations = _build_delta_recommendations(
        delta_true_peak_db=delta_true_peak,
        delta_loudness_db=delta_loudness,
        delta_crest_factor_db=delta_crest,
        clipping_removed=clipping_removed,
    )
    return QualityDeltaReport(
        source_before=before.source,
        source_after=after.source,
        delta_true_peak_db=delta_true_peak,
        delta_loudness_db=delta_loudness,
        delta_crest_factor_db=delta_crest,
        delta_dynamic_range_db=delta_dynamic_range,
        clipping_removed=clipping_removed,
        recommendations=recommendations,
    )


def _build_delta_recommendations(
    *,
    delta_true_peak_db: float,
    delta_loudness_db: float,
    delta_crest_factor_db: float,
    clipping_removed: bool,
) -> tuple[str, ...]:
    recommendations: list[str] = []
    if clipping_removed:
        recommendations.append("Clipping removed compared to input.")
    if delta_true_peak_db > 1.0:
        recommendations.append("True peak increased noticeably: consider lower limiter ceiling.")
    elif delta_true_peak_db < -3.0:
        recommendations.append("True peak dropped strongly: check if output is too conservative.")
    if delta_loudness_db > 3.0:
        recommendations.append("Output is much louder than input: verify streaming loudness target.")
    elif delta_loudness_db < -3.0:
        recommendations.append("Output is much quieter than input: consider more makeup gain.")
    if delta_crest_factor_db < -2.0:
        recommendations.append("Crest factor reduced: compression may be too aggressive.")
    if not recommendations:
        recommendations.append("Before/after metrics are within expected range.")
    return tuple(recommendations)

