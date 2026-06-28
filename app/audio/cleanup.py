from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.audio.format import ensure_audio_shape, to_mono


@dataclass(frozen=True)
class CleanupSettings:
    remove_dc_offset: bool = True
    fade_ms: float = 5.0
    noise_gate_db: float = -55.0
    trim_silence_db: float = -60.0
    trim_silence_enabled: bool = False
    gain_stage_target_db: float | None = None

    @classmethod
    def from_mapping(cls, data: dict | None = None) -> "CleanupSettings":
        data = data or {}
        gain_stage_target_db = data.get("gain_stage_target_db")
        return cls(
            remove_dc_offset=bool(data.get("remove_dc_offset", True)),
            fade_ms=float(data.get("fade_ms", 5.0)),
            noise_gate_db=float(data.get("noise_gate_db", -55.0)),
            trim_silence_db=float(data.get("trim_silence_db", -60.0)),
            trim_silence_enabled=bool(data.get("trim_silence_enabled", False)),
            gain_stage_target_db=float(gain_stage_target_db) if gain_stage_target_db is not None else None,
        )


def peak_normalize(audio: np.ndarray, target_db: float = -1.0) -> np.ndarray:
    array = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
    peak = float(np.max(np.abs(array))) if array.size else 0.0
    if peak == 0.0:
        return array
    target_amp = 10 ** (target_db / 20)
    return array * (target_amp / peak)


def basic_cleanup(audio: np.ndarray) -> np.ndarray:
    """Lekki etap bezpieczeństwa: usuwa NaN/inf i bardzo ciche artefakty numeryczne."""
    cleaned = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
    cleaned = np.nan_to_num(cleaned, nan=0.0, posinf=0.0, neginf=0.0)
    cleaned[np.abs(cleaned) < 1e-8] = 0.0
    return cleaned


def process_cleanup(audio: np.ndarray, sample_rate: int, settings: CleanupSettings | None = None) -> np.ndarray:
    cfg = settings or CleanupSettings()
    work = basic_cleanup(audio)
    if cfg.remove_dc_offset:
        work = remove_dc_offset(work)
    work = apply_noise_gate(work, cfg.noise_gate_db)
    if cfg.trim_silence_enabled:
        work = trim_silence(work, cfg.trim_silence_db)
    work = apply_fade_safety(work, sample_rate, cfg.fade_ms)
    if cfg.gain_stage_target_db is not None:
        work = gain_stage(work, cfg.gain_stage_target_db)
    return work


def remove_dc_offset(audio: np.ndarray) -> np.ndarray:
    work = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
    if work.ndim == 1:
        return work - float(np.mean(work))
    return work - np.mean(work, axis=0, keepdims=True)


def apply_fade_safety(audio: np.ndarray, sample_rate: int, fade_ms: float) -> np.ndarray:
    work = ensure_audio_shape(np.asarray(audio, dtype=np.float64)).copy()
    if sample_rate <= 0 or fade_ms <= 0.0 or work.size == 0:
        return work
    fade_samples = min(int(sample_rate * fade_ms / 1000.0), work.shape[0] // 2)
    if fade_samples <= 0:
        return work
    ramp = np.linspace(0.0, 1.0, fade_samples, endpoint=True)
    if work.ndim == 1:
        work[:fade_samples] *= ramp
        work[-fade_samples:] *= ramp[::-1]
    else:
        work[:fade_samples, :] *= ramp[:, None]
        work[-fade_samples:, :] *= ramp[::-1, None]
    return work


def apply_noise_gate(audio: np.ndarray, threshold_db: float) -> np.ndarray:
    work = ensure_audio_shape(np.asarray(audio, dtype=np.float64)).copy()
    threshold = 10 ** (threshold_db / 20.0)
    work[np.abs(work) < threshold] = 0.0
    return work


def trim_silence(audio: np.ndarray, threshold_db: float) -> np.ndarray:
    work = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
    if work.size == 0:
        return work
    mono = np.abs(to_mono(work))
    threshold = 10 ** (threshold_db / 20.0)
    active = np.flatnonzero(mono >= threshold)
    if active.size == 0:
        return work[:0] if work.ndim == 1 else work[:0, :]
    start = int(active[0])
    end = int(active[-1]) + 1
    return work[start:end] if work.ndim == 1 else work[start:end, :]


def gain_stage(audio: np.ndarray, target_rms_db: float) -> np.ndarray:
    work = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
    mono = to_mono(work)
    rms = float(np.sqrt(np.mean(np.square(mono)))) if mono.size else 0.0
    if rms <= 0.0:
        return work
    current_db = 20.0 * np.log10(max(rms, 1e-12))
    gain = 10 ** ((target_rms_db - current_db) / 20.0)
    return work * gain
