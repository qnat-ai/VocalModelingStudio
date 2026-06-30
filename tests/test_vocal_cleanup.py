from __future__ import annotations

import numpy as np

from app.audio.cleanup import CleanupSettings, high_pass_filter, process_cleanup_with_report


def test_cleanup_disabled_keeps_basic_report() -> None:
    audio = np.array([0.0, 0.1, -0.1, 0.2], dtype=np.float64)
    cleaned, report = process_cleanup_with_report(audio, 48000, CleanupSettings(enabled=False))
    assert cleaned.shape == audio.shape
    assert report.enabled is False
    assert "basic_numeric_cleanup" in report.applied_steps


def test_high_pass_filter_reduces_dc_component() -> None:
    dc_heavy = np.ones(4096, dtype=np.float64) * 0.3
    filtered = high_pass_filter(dc_heavy, sample_rate=48000, cutoff_hz=80.0, order=2)
    assert float(np.mean(np.abs(filtered))) < 0.05


def test_cleanup_report_contains_steps_when_enabled() -> None:
    audio = np.sin(np.linspace(0.0, 10.0, 4096, endpoint=False)).astype(np.float64)
    settings = CleanupSettings(enabled=True, remove_dc_offset=True, high_pass_enabled=True, noise_gate_enabled=False)
    _, report = process_cleanup_with_report(audio, 48000, settings)
    assert report.enabled is True
    assert any(step.startswith("high_pass_") for step in report.applied_steps)
    assert report.input_samples >= report.output_samples

