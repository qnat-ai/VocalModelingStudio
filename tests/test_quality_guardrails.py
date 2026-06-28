from __future__ import annotations

from app.analysis.quality_guardrails import GuardrailSettings, evaluate_guardrails
from app.analysis.quality_report import QualityReport


def test_guardrails_pass_for_reasonable_report():
    report = QualityReport(
        true_peak_dbfs=-2.0,
        loudness_estimate_dbfs=-16.0,
        crest_factor_db=8.0,
        clipped_samples=0,
    )

    result = evaluate_guardrails(report)

    assert result.passed is True
    assert result.issues == ()


def test_guardrails_fail_for_hot_and_clipped_report():
    report = QualityReport(
        true_peak_dbfs=-0.1,
        loudness_estimate_dbfs=-10.0,
        crest_factor_db=3.0,
        clipped_samples=14,
    )

    result = evaluate_guardrails(report, GuardrailSettings(max_clipped_samples=0))

    assert result.passed is False
    assert len(result.issues) >= 3

