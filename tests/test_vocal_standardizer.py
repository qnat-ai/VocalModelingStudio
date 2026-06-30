from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import soundfile as sf

from app.standardization.vocal_standardizer import (
    VocalInstrumentalStandardizer,
    analyze_track,
    build_preview_mix,
)


def _write_sine(path: Path, *, amp: float, sr: int = 24000, seconds: float = 0.25, freq: float = 440.0) -> Path:
    t = np.linspace(0.0, seconds, int(sr * seconds), endpoint=False)
    audio = amp * np.sin(2.0 * np.pi * freq * t)
    sf.write(path, audio, sr)
    return path


def test_analyze_track_basic_metrics() -> None:
    sr = 24000
    audio = np.array([0.0, 0.25, -0.25, 0.5, -0.5], dtype=np.float64)
    metrics = analyze_track(audio, sr, source="synthetic")
    assert metrics.source == "synthetic"
    assert metrics.channels == 1
    assert metrics.peak > 0.49
    assert metrics.rms > 0.0
    assert metrics.clipping is False


def test_standardizer_renders_processed_vocal_and_keeps_instrumental_reference(tmp_path: Path) -> None:
    vocal = _write_sine(tmp_path / "vocal.wav", amp=0.08)
    instrumental = _write_sine(tmp_path / "instrumental.wav", amp=0.35, freq=220.0)
    out_dir = tmp_path / "out"

    standardizer = VocalInstrumentalStandardizer(sample_rate=24000, output_dir=out_dir)
    result = standardizer.render(vocal_path=vocal, instrumental_path=instrumental, action="accept")

    assert result.vocal_path is not None
    assert result.vocal_path.name == "vocal_processed.wav"
    assert result.vocal_path.exists()
    assert result.preview_mix_path is not None
    assert result.preview_mix_path.name == "preview_mix.wav"
    assert result.preview_mix_path.exists()
    assert result.report_path.exists()

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report["output_vocal_path"].endswith("vocal_processed.wav")
    assert report["preview_mix_path"].endswith("preview_mix.wav")
    assert "instrumental" in report["instrumental_metrics"]["source"]
    assert instrumental.exists(), "Instrumental reference file must not be modified or removed."


def test_correct_action_uses_manual_gain(tmp_path: Path) -> None:
    vocal = _write_sine(tmp_path / "vocal.wav", amp=0.10)
    standardizer = VocalInstrumentalStandardizer(sample_rate=24000, output_dir=tmp_path / "out")
    result = standardizer.render(vocal_path=vocal, action="correct", manual_gain_db=2.5)
    assert result.report.applied_vocal_gain_db == 2.5


def test_preview_mix_matches_longer_length() -> None:
    vocal = np.ones(1000, dtype=np.float64) * 0.1
    instrumental = np.ones((1500, 2), dtype=np.float64) * 0.2
    preview = build_preview_mix(vocal, instrumental)
    assert preview.shape == (1500, 2)
