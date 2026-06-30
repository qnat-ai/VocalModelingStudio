from __future__ import annotations

import numpy as np

from app.audio.cleanup import (
    CleanupSettings,
    apply_de_esser,
    apply_noise_gate,
    high_pass_filter,
    process_cleanup_with_report,
)


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


def test_de_esser_reduces_sibilant_band_energy() -> None:
    sr = 48000
    t = np.linspace(0.0, 1.0, sr, endpoint=False)
    low = 0.10 * np.sin(2.0 * np.pi * 300.0 * t)
    sib = 0.40 * np.sin(2.0 * np.pi * 7000.0 * t)
    audio = low + sib

    processed = apply_de_esser(
        audio,
        sample_rate=sr,
        threshold_db=-35.0,
        ratio=6.0,
        max_reduction_db=12.0,
        band_low_hz=5000.0,
        band_high_hz=9000.0,
    )

    spec_before = np.abs(np.fft.rfft(audio))
    spec_after = np.abs(np.fft.rfft(processed))
    freqs = np.fft.rfftfreq(audio.size, d=1.0 / sr)
    sib_bin = int(np.argmin(np.abs(freqs - 7000.0)))
    before_sibilant = float(spec_before[sib_bin])
    after_sibilant = float(spec_after[sib_bin])
    assert after_sibilant < before_sibilant


def test_de_esser_stronger_ratio_reduces_more() -> None:
    sr = 48000
    t = np.linspace(0.0, 0.6, int(sr * 0.6), endpoint=False)
    audio = 0.08 * np.sin(2.0 * np.pi * 250.0 * t) + 0.35 * np.sin(2.0 * np.pi * 7500.0 * t)

    mild = apply_de_esser(audio, sample_rate=sr, threshold_db=-34.0, ratio=2.0, max_reduction_db=6.0)
    strong = apply_de_esser(audio, sample_rate=sr, threshold_db=-34.0, ratio=6.0, max_reduction_db=12.0)

    freqs = np.fft.rfftfreq(audio.size, d=1.0 / sr)
    sib_bin = int(np.argmin(np.abs(freqs - 7500.0)))
    mild_energy = float(np.abs(np.fft.rfft(mild))[sib_bin])
    strong_energy = float(np.abs(np.fft.rfft(strong))[sib_bin])
    assert strong_energy < mild_energy


def test_cleanup_report_de_esser_metrics_populated() -> None:
    sr = 48000
    t = np.linspace(0.0, 1.0, sr, endpoint=False)
    audio = 0.08 * np.sin(2.0 * np.pi * 300.0 * t) + 0.35 * np.sin(2.0 * np.pi * 7000.0 * t)
    settings = CleanupSettings(
        enabled=True,
        high_pass_enabled=False,
        de_esser_enabled=True,
        de_esser_threshold_db=-35.0,
        de_esser_ratio=6.0,
        de_esser_max_reduction_db=12.0,
        de_esser_band_low_hz=5000.0,
        de_esser_band_high_hz=9000.0,
    )
    _, report = process_cleanup_with_report(audio, sr, settings)

    assert report.de_esser_active is True
    assert report.de_esser_sibilant_band_before_rms > -240.0
    assert report.de_esser_sibilant_band_after_rms > -240.0
    assert report.de_esser_estimated_reduction_db >= 0.0
    assert report.de_esser_sibilant_band_after_rms <= report.de_esser_sibilant_band_before_rms


def test_cleanup_report_intensity_and_risk_de_esser_gate() -> None:
    sr = 48000
    audio = np.sin(np.linspace(0.0, 5.0, sr * 2, endpoint=False)).astype(np.float64) * 0.2
    settings = CleanupSettings(
        enabled=True,
        high_pass_enabled=True,
        high_pass_hz=120.0,
        de_esser_enabled=True,
        noise_gate_enabled=True,
    )
    _, report = process_cleanup_with_report(audio, sr, settings)

    assert report.cleanup_intensity in {"medium", "strong"}
    assert report.risk_level in {"medium", "high"}
    assert len(report.risk_warnings) >= 2


def test_cleanup_report_light_when_only_safe_steps() -> None:
    sr = 48000
    audio = np.sin(np.linspace(0.0, 2.0, sr, endpoint=False)).astype(np.float64) * 0.15
    settings = CleanupSettings(
        enabled=True,
        remove_dc_offset=True,
        high_pass_enabled=True,
        high_pass_hz=80.0,
        de_esser_enabled=False,
        noise_gate_enabled=False,
        trim_silence_enabled=False,
        gain_stage_target_db=None,
    )
    _, report = process_cleanup_with_report(audio, sr, settings)

    assert report.cleanup_intensity in {"none", "light"}
    assert report.risk_level == "low"
    assert report.de_esser_active is False


def test_noise_gate_adaptive_reduces_quiet_tail() -> None:
    sr = 48000
    voice = np.ones(int(0.25 * sr), dtype=np.float64) * 0.12
    tail = np.ones(int(0.25 * sr), dtype=np.float64) * 0.002
    audio = np.concatenate([voice, tail])

    gated = apply_noise_gate(
        audio,
        threshold_db=-46.0,
        floor_db=-30.0,
        attack_ms=2.0,
        release_ms=40.0,
        hold_ms=8.0,
        sample_rate=sr,
    )

    tail_before = float(np.mean(np.abs(audio[-int(0.1 * sr) :])))
    tail_after = float(np.mean(np.abs(gated[-int(0.1 * sr) :])))
    assert tail_after < tail_before


