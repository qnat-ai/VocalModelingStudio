from __future__ import annotations

import numpy as np
import soundfile as sf

from app.analysis.quality_report import analyze_audio, analyze_quality


def test_quality_report_detects_basic_metrics(tmp_path):
    sample_rate = 48_000
    seconds = 1.0
    time = np.linspace(0.0, seconds, int(sample_rate * seconds), endpoint=False)
    audio = 0.2 * np.sin(2 * np.pi * 220.0 * time)
    path = tmp_path / "voice.wav"
    sf.write(path, audio, sample_rate)

    report = analyze_quality(path)

    assert report.source == str(path)
    assert report.sample_rate == sample_rate
    assert report.channels == 1
    assert abs(report.duration_sec - 1.0) < 1e-6
    assert report.peak > 0.0
    assert report.rms > 0.0
    assert report.true_peak_dbfs < 0.0
    assert report.loudness_estimate_dbfs < 0.0
    assert report.dynamic_range_db >= 0.0
    assert len(report.recommendations) >= 1
    assert report.clipping is False
    assert report.to_dict()["source"] == str(path)

    array_report = analyze_audio(audio, sample_rate, source="buffer")
    assert array_report.source == "buffer"
    assert array_report.noise_level in {"very-low", "low", "moderate", "high"}
    assert isinstance(array_report.recommendations, tuple)


