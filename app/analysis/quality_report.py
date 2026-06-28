"""Audio quality report helpers."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import librosa
import numpy as np
import soundfile as sf

from app.audio.format import ensure_audio_shape, to_mono


@dataclass(frozen=True)
class QualityReport:
    noise_level: str = "unknown"
    clipping: bool = False
    notes: str = "Analysis not implemented yet."
    source: str = ""
    sample_rate: int = 0
    channels: int = 0
    duration_sec: float = 0.0
    peak: float = 0.0
    rms: float = 0.0
    crest_factor_db: float = 0.0
    clipped_samples: int = 0
    zero_crossing_rate: float = 0.0
    true_peak_dbfs: float = 0.0
    loudness_estimate_dbfs: float = 0.0
    dynamic_range_db: float = 0.0
    recommendations: tuple[str, ...] = ()
    spectral_centroid_hz: float = 0.0
    spectral_rolloff_hz: float = 0.0
    silence_ratio: float = 0.0
    peak_per_channel: tuple[float, ...] = ()
    rms_per_channel: tuple[float, ...] = ()
    clipped_samples_per_channel: tuple[int, ...] = ()
    vocal_readiness: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def analyze_audio(audio: np.ndarray, sample_rate: int, *, source: str = "") -> QualityReport:
    array = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
    if array.size == 0:
        return QualityReport(source=source, sample_rate=int(sample_rate), notes="Empty audio buffer.")

    if array.ndim == 1:
        channels = 1
        mono = array
        channel_view = array[:, None]
    elif array.ndim == 2:
        channels = int(array.shape[1])
        mono = to_mono(array)
        channel_view = array
    else:
        flattened = array.reshape(-1)
        channels = 1
        mono = flattened
        array = flattened
        channel_view = flattened[:, None]

    peak = float(np.max(np.abs(array)))
    rms = float(np.sqrt(np.mean(np.square(array))))
    duration_sec = float(array.shape[0] / sample_rate) if sample_rate else 0.0
    clipped_samples = int(np.count_nonzero(np.abs(array) >= 0.999))
    clipping = clipped_samples > 0
    crest_factor_db = float(20.0 * np.log10(peak / rms)) if peak > 0.0 and rms > 0.0 else 0.0
    true_peak_dbfs = float(20.0 * np.log10(max(peak, 1e-12)))
    loudness_estimate_dbfs = float(20.0 * np.log10(max(rms, 1e-12)))

    if mono.size > 1:
        zero_crossings = np.count_nonzero(np.diff(np.signbit(mono)))
        zero_crossing_rate = float(zero_crossings / (mono.size - 1))
    else:
        zero_crossing_rate = 0.0

    abs_mono = np.abs(mono)
    p95 = float(np.percentile(abs_mono, 95)) if abs_mono.size else 0.0
    p10 = float(np.percentile(abs_mono, 10)) if abs_mono.size else 0.0
    dynamic_range_db = float(20.0 * np.log10(p95 / p10)) if p95 > 0.0 and p10 > 0.0 else 0.0
    silence_threshold = 10 ** (-55.0 / 20.0)
    silence_ratio = float(np.mean(abs_mono < silence_threshold)) if abs_mono.size else 0.0

    peak_per_channel = tuple(float(np.max(np.abs(channel_view[:, idx]))) for idx in range(channel_view.shape[1]))
    rms_per_channel = tuple(
        float(np.sqrt(np.mean(np.square(channel_view[:, idx])))) for idx in range(channel_view.shape[1])
    )
    clipped_samples_per_channel = tuple(
        int(np.count_nonzero(np.abs(channel_view[:, idx]) >= 0.999)) for idx in range(channel_view.shape[1])
    )

    if mono.size >= 512 and sample_rate > 0:
        spectral_centroid_hz = float(np.mean(librosa.feature.spectral_centroid(y=mono, sr=sample_rate)))
        spectral_rolloff_hz = float(np.mean(librosa.feature.spectral_rolloff(y=mono, sr=sample_rate)))
    else:
        spectral_centroid_hz = 0.0
        spectral_rolloff_hz = 0.0

    if rms < 0.005:
        noise_level = "very-low"
    elif rms < 0.02:
        noise_level = "low"
    elif rms < 0.05:
        noise_level = "moderate"
    else:
        noise_level = "high"

    notes = "Statystyki amplitudy, clipów i zera-crossingu obliczone lokalnie."
    recommendations = _build_recommendations(
        clipping=clipping,
        clipped_samples=clipped_samples,
        loudness_estimate_dbfs=loudness_estimate_dbfs,
        crest_factor_db=crest_factor_db,
        zero_crossing_rate=zero_crossing_rate,
    )
    vocal_readiness = _estimate_vocal_readiness(
        clipping=clipping,
        loudness_estimate_dbfs=loudness_estimate_dbfs,
        silence_ratio=silence_ratio,
        zero_crossing_rate=zero_crossing_rate,
    )
    return QualityReport(
        noise_level=noise_level,
        clipping=clipping,
        notes=notes,
        source=source,
        sample_rate=int(sample_rate),
        channels=channels,
        duration_sec=duration_sec,
        peak=peak,
        rms=rms,
        crest_factor_db=crest_factor_db,
        clipped_samples=clipped_samples,
        zero_crossing_rate=zero_crossing_rate,
        true_peak_dbfs=true_peak_dbfs,
        loudness_estimate_dbfs=loudness_estimate_dbfs,
        dynamic_range_db=dynamic_range_db,
        recommendations=recommendations,
        spectral_centroid_hz=spectral_centroid_hz,
        spectral_rolloff_hz=spectral_rolloff_hz,
        silence_ratio=silence_ratio,
        peak_per_channel=peak_per_channel,
        rms_per_channel=rms_per_channel,
        clipped_samples_per_channel=clipped_samples_per_channel,
        vocal_readiness=vocal_readiness,
    )


def analyze_quality(audio_path: Path) -> QualityReport:
    audio, sr = sf.read(audio_path, always_2d=False)
    return analyze_audio(np.asarray(audio), int(sr), source=str(audio_path))


def _build_recommendations(
    *,
    clipping: bool,
    clipped_samples: int,
    loudness_estimate_dbfs: float,
    crest_factor_db: float,
    zero_crossing_rate: float,
) -> tuple[str, ...]:
    recommendations: list[str] = []
    if clipping:
        recommendations.append(f"Detected clipping ({clipped_samples} samples): lower input gain or limiter ceiling.")
    if loudness_estimate_dbfs < -24.0:
        recommendations.append("Signal is quiet: consider additional makeup gain before limiting.")
    elif loudness_estimate_dbfs > -12.0:
        recommendations.append("Signal is hot: reduce compression/makeup gain to preserve headroom.")
    if 0.0 < crest_factor_db < 5.0:
        recommendations.append("Low crest factor: likely over-compressed, reduce ratio or raise threshold.")
    if zero_crossing_rate > 0.25:
        recommendations.append("High zero-crossing rate: check for hiss or harsh high-frequency content.")
    if not recommendations:
        recommendations.append("No critical quality issues detected.")
    return tuple(recommendations)


def _estimate_vocal_readiness(
    *,
    clipping: bool,
    loudness_estimate_dbfs: float,
    silence_ratio: float,
    zero_crossing_rate: float,
) -> str:
    if clipping or loudness_estimate_dbfs > -10.0:
        return "needs-fix"
    if silence_ratio > 0.75 or zero_crossing_rate > 0.3:
        return "needs-cleanup"
    if -24.0 <= loudness_estimate_dbfs <= -12.0:
        return "ready-for-processing"
    return "review"


