from __future__ import annotations

import json

import numpy as np
import soundfile as sf

from app.core.pipeline import VocalPipeline


def test_pipeline_fail_safe_and_reports(tmp_path, monkeypatch):
    sample_rate = 48_000
    seconds = 1.0
    time = np.linspace(0.0, seconds, int(sample_rate * seconds), endpoint=False)
    audio = 0.95 * np.sin(2 * np.pi * 220.0 * time)
    input_path = tmp_path / "input.wav"
    output_path = tmp_path / "output.wav"
    out_dir = tmp_path / "out"
    projects_dir = tmp_path / "projects"
    sf.write(input_path, audio, sample_rate)

    def fake_estimate_f0_mono(signal, sr):
        _ = signal, sr
        return np.array([0.0, 0.5, 1.0]), np.array([220.0, 220.0, 220.0])

    monkeypatch.setattr("app.core.pipeline.estimate_f0_mono", fake_estimate_f0_mono)

    config = {
        "audio": {"sample_rate": sample_rate, "normalize_peak_db": -1.0},
        "processing": {
            "pitch_correction_enabled": False,
            "voice_conversion_enabled": False,
        },
        "paths": {"projects_dir": str(projects_dir), "output_dir": str(out_dir), "logs_dir": str(tmp_path / "logs")},
        "mastering": {
            "enable_highpass": True,
            "highpass_hz": 80.0,
            "compressor_threshold_db": -18.0,
            "compressor_ratio": 2.0,
            "limiter_ceiling_db": -1.0,
            "makeup_gain_db": 0.0,
            "adaptive_enabled": True,
        },
        "quality_guardrails": {
            "max_true_peak_dbfs": -10.0,
            "min_loudness_dbfs": -20.0,
            "max_loudness_dbfs": -14.0,
            "max_clipped_samples": 0,
            "min_crest_factor_db": 4.0,
            "fail_safe_enabled": True,
            "neutral_mastering": {
                "limiter_ceiling_db": -12.0,
                "compressor_ratio": 1.3,
                "adaptive_enabled": False,
            },
        },
    }

    result = VocalPipeline(config).run(input_path=input_path, output_path=output_path)

    assert result == output_path
    assert output_path.exists()

    sessions = list(projects_dir.glob("*_input"))
    assert sessions
    session_dir = sessions[0]

    guardrail_path = session_dir / "reports" / f"quality_guardrails_{input_path.stem}.json"
    delta_path = session_dir / "reports" / f"quality_delta_{input_path.stem}.json"
    assert guardrail_path.exists()
    assert delta_path.exists()

    metadata_files = sorted((session_dir / "metadata").glob(f"render_metadata_{input_path.stem}_*.json"))
    assert metadata_files
    metadata = json.loads(metadata_files[-1].read_text(encoding="utf-8"))
    assert metadata["fail_safe_enabled"] is True
    assert metadata["fail_safe_activated"] is True
    assert float(metadata["mastering_profile"]["limiter_ceiling_db"]) == -12.0

