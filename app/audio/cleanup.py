from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from scipy.signal import butter, sosfilt, sosfiltfilt

from app.audio.format import ensure_audio_shape, to_mono

_EPS = 1e-12


@dataclass(frozen=True)
class CleanupSettings:
    enabled: bool = True
    remove_dc_offset: bool = True
    high_pass_enabled: bool = True
    high_pass_hz: float = 80.0
    high_pass_order: int = 2
    fade_ms: float = 5.0
    noise_gate_enabled: bool = False
    noise_gate_db: float = -55.0
    trim_silence_db: float = -60.0
    trim_silence_enabled: bool = False
    trim_padding_ms: float = 50.0
    gain_stage_target_db: float | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None = None) -> "CleanupSettings":
        data = data or {}
        gain_stage_target_db = data.get("gain_stage_target_db")
        return cls(
            enabled=bool(data.get("enabled", True)),
            remove_dc_offset=bool(data.get("remove_dc_offset", True)),
            high_pass_enabled=bool(data.get("high_pass_enabled", True)),
            high_pass_hz=float(data.get("high_pass_hz", 80.0)),
            high_pass_order=int(data.get("high_pass_order", 2)),
            fade_ms=float(data.get("fade_ms", 5.0)),
            noise_gate_enabled=bool(data.get("noise_gate_enabled", False)),
            noise_gate_db=float(data.get("noise_gate_db", -55.0)),
            trim_silence_db=float(data.get("trim_silence_db", -60.0)),
            trim_silence_enabled=bool(data.get("trim_silence_enabled", False)),
            trim_padding_ms=float(data.get("trim_padding_ms", 50.0)),
            gain_stage_target_db=float(gain_stage_target_db) if gain_stage_target_db is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CleanupReport:
    enabled: bool
    settings: dict[str, Any]
    applied_steps: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    input_peak_dbfs: float = -240.0
    output_peak_dbfs: float = -240.0
    input_rms_dbfs: float = -240.0
    output_rms_dbfs: float = -240.0
    input_samples: int = 0
    output_samples: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_text_lines(self) -> list[str]:
        lines = [
            "Cleanup wokalu:",
            f"- aktywny: {'tak' if self.enabled else 'nie'}",
            f"- peak przed/po: {self.input_peak_dbfs:.2f} / {self.output_peak_dbfs:.2f} dBFS",
            f"- RMS przed/po: {self.input_rms_dbfs:.2f} / {self.output_rms_dbfs:.2f} dBFS",
        ]
        if self.applied_steps:
            lines.append("- zastosowane kroki: " + ", ".join(self.applied_steps))
        if self.warnings:
            lines.append("- ostrzeżenia: " + "; ".join(self.warnings))
        return lines


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
    cleaned, _ = process_cleanup_with_report(audio, sample_rate, settings)
    return cleaned


def process_cleanup_with_report(
    audio: np.ndarray,
    sample_rate: int,
    settings: CleanupSettings | None = None,
) -> tuple[np.ndarray, CleanupReport]:
    cfg = settings or CleanupSettings()
    work = basic_cleanup(audio)
    input_peak_dbfs, input_rms_dbfs = _quick_metrics(work)
    applied_steps: list[str] = ["basic_numeric_cleanup"]
    warnings: list[str] = []

    if not cfg.enabled:
        output_peak_dbfs, output_rms_dbfs = _quick_metrics(work)
        return work, CleanupReport(
            enabled=False,
            settings=cfg.to_dict(),
            applied_steps=tuple(applied_steps),
            warnings=("Cleanup wyłączony; wykonano tylko podstawowe zabezpieczenie numeryczne.",),
            input_peak_dbfs=input_peak_dbfs,
            output_peak_dbfs=output_peak_dbfs,
            input_rms_dbfs=input_rms_dbfs,
            output_rms_dbfs=output_rms_dbfs,
            input_samples=int(ensure_audio_shape(audio).shape[0]),
            output_samples=int(work.shape[0]),
        )

    if cfg.remove_dc_offset:
        work = remove_dc_offset(work)
        applied_steps.append("remove_dc_offset")

    if cfg.high_pass_enabled:
        try:
            work = high_pass_filter(
                work,
                sample_rate=sample_rate,
                cutoff_hz=cfg.high_pass_hz,
                order=cfg.high_pass_order,
            )
            applied_steps.append(f"high_pass_{cfg.high_pass_hz:.0f}hz")
        except ValueError as exc:
            warnings.append(f"Pominięto high-pass: {exc}")

    if cfg.noise_gate_enabled:
        work = apply_noise_gate(work, cfg.noise_gate_db)
        applied_steps.append(f"noise_gate_{cfg.noise_gate_db:.0f}db")

    if cfg.trim_silence_enabled:
        before_samples = int(work.shape[0])
        work = trim_silence(work, sample_rate=sample_rate, threshold_db=cfg.trim_silence_db, padding_ms=cfg.trim_padding_ms)
        after_samples = int(work.shape[0])
        applied_steps.append(f"trim_silence_{cfg.trim_silence_db:.0f}db")
        if after_samples < before_samples:
            warnings.append(f"Trim silence skrócił plik z {before_samples} do {after_samples} próbek.")

    work = apply_fade_safety(work, sample_rate, cfg.fade_ms)
    if cfg.fade_ms > 0.0:
        applied_steps.append(f"fade_safety_{cfg.fade_ms:.1f}ms")

    if cfg.gain_stage_target_db is not None:
        work = gain_stage(work, cfg.gain_stage_target_db)
        applied_steps.append(f"gain_stage_rms_{cfg.gain_stage_target_db:.1f}dbfs")

    output_peak_dbfs, output_rms_dbfs = _quick_metrics(work)
    return work, CleanupReport(
        enabled=True,
        settings=cfg.to_dict(),
        applied_steps=tuple(applied_steps),
        warnings=tuple(warnings),
        input_peak_dbfs=input_peak_dbfs,
        output_peak_dbfs=output_peak_dbfs,
        input_rms_dbfs=input_rms_dbfs,
        output_rms_dbfs=output_rms_dbfs,
        input_samples=int(ensure_audio_shape(audio).shape[0]),
        output_samples=int(work.shape[0]),
    )


def remove_dc_offset(audio: np.ndarray) -> np.ndarray:
    work = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
    if work.ndim == 1:
        return work - float(np.mean(work))
    return work - np.mean(work, axis=0, keepdims=True)


def high_pass_filter(
    audio: np.ndarray,
    *,
    sample_rate: int,
    cutoff_hz: float = 80.0,
    order: int = 2,
) -> np.ndarray:
    work = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
    if sample_rate <= 0:
        raise ValueError("sample_rate musi być dodatni")
    nyquist = sample_rate / 2.0
    if cutoff_hz <= 0:
        return work
    if cutoff_hz >= nyquist:
        raise ValueError("high_pass_hz musi być niższy niż Nyquist")
    if work.shape[0] < max(16, int(order) * 6):
        return work

    sos = butter(int(order), float(cutoff_hz), btype="highpass", fs=float(sample_rate), output="sos")
    try:
        return sosfiltfilt(sos, work, axis=0)
    except ValueError:
        return sosfilt(sos, work, axis=0)


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


def trim_silence(
    audio: np.ndarray,
    *,
    sample_rate: int,
    threshold_db: float,
    padding_ms: float = 50.0,
) -> np.ndarray:
    work = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
    if work.size == 0:
        return work
    mono = np.abs(to_mono(work))
    threshold = 10 ** (threshold_db / 20.0)
    active = np.flatnonzero(mono >= threshold)
    if active.size == 0:
        return work[:0] if work.ndim == 1 else work[:0, :]
    padding_samples = int(max(0.0, padding_ms) * max(sample_rate, 1) / 1000.0)
    start = max(0, int(active[0]) - padding_samples)
    end = min(work.shape[0], int(active[-1]) + 1 + padding_samples)
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


def _quick_metrics(audio: np.ndarray) -> tuple[float, float]:
    work = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
    if work.size == 0:
        return -240.0, -240.0
    peak = float(np.max(np.abs(work)))
    mono = to_mono(work)
    rms = float(np.sqrt(np.mean(np.square(mono)))) if mono.size else 0.0
    peak_dbfs = float(20.0 * np.log10(max(peak, _EPS)))
    rms_dbfs = float(20.0 * np.log10(max(rms, _EPS)))
    return peak_dbfs, rms_dbfs

