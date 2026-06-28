"""Basic mastering metering helpers."""
from __future__ import annotations

import numpy as np

from app.audio.format import ensure_audio_shape, to_mono


def measure_rms_dbfs(audio: np.ndarray) -> float:
    mono = to_mono(audio)
    rms = float(np.sqrt(np.mean(np.square(mono)))) if mono.size else 0.0
    return float(20.0 * np.log10(max(rms, 1e-12)))


def measure_peak(audio: np.ndarray) -> float:
    array = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
    return float(np.max(np.abs(array))) if array.size else 0.0


def measure_crest_factor_db(audio: np.ndarray) -> float:
    mono = to_mono(audio)
    rms = float(np.sqrt(np.mean(np.square(mono)))) if mono.size else 0.0
    peak = float(np.max(np.abs(mono))) if mono.size else 0.0
    if peak <= 0.0 or rms <= 0.0:
        return 0.0
    return float(20.0 * np.log10(peak / rms))

