"""Output quality guardrails and validation helpers."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from app.analysis.quality_report import QualityReport


@dataclass(frozen=True)
class GuardrailSettings:
    max_true_peak_dbfs: float = -1.0
    min_loudness_dbfs: float = -19.0
    max_loudness_dbfs: float = -14.0
    max_clipped_samples: int = 0
    min_crest_factor_db: float = 4.5

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None = None) -> "GuardrailSettings":
        data = data or {}
        return cls(
            max_true_peak_dbfs=float(data.get("max_true_peak_dbfs", -1.0)),
            min_loudness_dbfs=float(data.get("min_loudness_dbfs", -19.0)),
            max_loudness_dbfs=float(data.get("max_loudness_dbfs", -14.0)),
            max_clipped_samples=int(data.get("max_clipped_samples", 0)),
            min_crest_factor_db=float(data.get("min_crest_factor_db", 4.5)),
        )


@dataclass(frozen=True)
class GuardrailResult:
    passed: bool
    issues: tuple[str, ...]
    evaluated_metrics: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def evaluate_guardrails(report: QualityReport, settings: GuardrailSettings | None = None) -> GuardrailResult:
    cfg = settings or GuardrailSettings()
    issues: list[str] = []

    if report.true_peak_dbfs > cfg.max_true_peak_dbfs:
        issues.append(
            f"True peak too high ({report.true_peak_dbfs:.2f} dBFS > {cfg.max_true_peak_dbfs:.2f} dBFS)."
        )
    if report.loudness_estimate_dbfs < cfg.min_loudness_dbfs:
        issues.append(
            f"Loudness too low ({report.loudness_estimate_dbfs:.2f} dBFS < {cfg.min_loudness_dbfs:.2f} dBFS)."
        )
    if report.loudness_estimate_dbfs > cfg.max_loudness_dbfs:
        issues.append(
            f"Loudness too high ({report.loudness_estimate_dbfs:.2f} dBFS > {cfg.max_loudness_dbfs:.2f} dBFS)."
        )
    if report.clipped_samples > cfg.max_clipped_samples:
        issues.append(
            f"Too many clipped samples ({report.clipped_samples} > {cfg.max_clipped_samples})."
        )
    if 0.0 < report.crest_factor_db < cfg.min_crest_factor_db:
        issues.append(
            f"Crest factor too low ({report.crest_factor_db:.2f} dB < {cfg.min_crest_factor_db:.2f} dB)."
        )

    metrics = {
        "true_peak_dbfs": report.true_peak_dbfs,
        "loudness_estimate_dbfs": report.loudness_estimate_dbfs,
        "crest_factor_db": report.crest_factor_db,
        "clipped_samples": float(report.clipped_samples),
    }
    return GuardrailResult(passed=not issues, issues=tuple(issues), evaluated_metrics=metrics)

