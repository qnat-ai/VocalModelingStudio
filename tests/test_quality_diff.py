from __future__ import annotations

from app.analysis.quality_diff import compare_quality_reports
from app.analysis.quality_report import QualityReport


def test_compare_quality_reports_returns_recommendations():
    before = QualityReport(
        source="before.wav",
        clipping=True,
        true_peak_dbfs=-0.1,
        loudness_estimate_dbfs=-9.0,
        crest_factor_db=5.0,
        dynamic_range_db=15.0,
    )
    after = QualityReport(
        source="after.wav",
        clipping=False,
        true_peak_dbfs=-6.0,
        loudness_estimate_dbfs=-16.0,
        crest_factor_db=7.5,
        dynamic_range_db=16.0,
    )

    delta = compare_quality_reports(before, after)

    assert delta.source_before == "before.wav"
    assert delta.source_after == "after.wav"
    assert delta.clipping_removed is True
    assert delta.delta_true_peak_db < 0.0
    assert len(delta.recommendations) >= 1

