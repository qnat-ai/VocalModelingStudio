from __future__ import annotations

from dataclasses import asdict, dataclass, field
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
    de_esser_enabled: bool = False
    de_esser_threshold_db: float = -28.0
    de_esser_ratio: float = 3.0
    de_esser_max_reduction_db: float = 8.0
    de_esser_band_low_hz: float = 4500.0
    de_esser_band_high_hz: float = 9500.0
    de_esser_attack_ms: float = 4.0
    de_esser_release_ms: float = 90.0
    de_esser_knee_db: float = 6.0
    de_esser_stereo_link: bool = True
    fade_ms: float = 5.0
    noise_gate_enabled: bool = False
    noise_gate_db: float = -55.0
    noise_gate_floor_db: float = -24.0
    noise_gate_attack_ms: float = 4.0
    noise_gate_release_ms: float = 80.0
    noise_gate_hold_ms: float = 20.0
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
            de_esser_enabled=bool(data.get("de_esser_enabled", False)),
            de_esser_threshold_db=float(data.get("de_esser_threshold_db", -28.0)),
            de_esser_ratio=float(data.get("de_esser_ratio", 3.0)),
            de_esser_max_reduction_db=float(data.get("de_esser_max_reduction_db", 8.0)),
            de_esser_band_low_hz=float(data.get("de_esser_band_low_hz", 4500.0)),
            de_esser_band_high_hz=float(data.get("de_esser_band_high_hz", 9500.0)),
            de_esser_attack_ms=float(data.get("de_esser_attack_ms", 4.0)),
            de_esser_release_ms=float(data.get("de_esser_release_ms", 90.0)),
            de_esser_knee_db=float(data.get("de_esser_knee_db", 6.0)),
            de_esser_stereo_link=bool(data.get("de_esser_stereo_link", True)),
            fade_ms=float(data.get("fade_ms", 5.0)),
            noise_gate_enabled=bool(data.get("noise_gate_enabled", False)),
            noise_gate_db=float(data.get("noise_gate_db", -55.0)),
            noise_gate_floor_db=float(data.get("noise_gate_floor_db", -24.0)),
            noise_gate_attack_ms=float(data.get("noise_gate_attack_ms", 4.0)),
            noise_gate_release_ms=float(data.get("noise_gate_release_ms", 80.0)),
            noise_gate_hold_ms=float(data.get("noise_gate_hold_ms", 20.0)),
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
    # --- de-esser detail ---
    de_esser_active: bool = False
    de_esser_estimated_reduction_db: float = 0.0
    de_esser_sibilant_band_before_rms: float = -240.0
    de_esser_sibilant_band_after_rms: float = -240.0
    # --- cleanup intensity / risk ---
    cleanup_intensity: str = "none"   # none | light | medium | strong
    risk_level: str = "low"           # low | medium | high
    risk_warnings: tuple[str, ...] = ()

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
        if self.de_esser_active:
            lines.append(
                f"- de-esser: aktywny | szacowana redukcja: {self.de_esser_estimated_reduction_db:.2f} dB"
                f" | sibilant RMS przed/po: {self.de_esser_sibilant_band_before_rms:.2f} / {self.de_esser_sibilant_band_after_rms:.2f} dBFS"
            )
        elif "de_esser" in " ".join(self.applied_steps):
            lines.append("- de-esser: włączony, brak mierzalnej redukcji")
        if self.enabled:
            lines.append(f"- intensywność cleanup: {self.cleanup_intensity} | ryzyko: {self.risk_level}")
        if self.risk_warnings:
            lines.extend(f"  ! {w}" for w in self.risk_warnings)
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

    # de-esser band metrics (initialized before potential early return)
    de_esser_active = False
    sib_band_before_rms = -240.0
    sib_band_after_rms = -240.0
    de_esser_estimated_reduction_db = 0.0

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

    if cfg.de_esser_enabled:
        try:
            sib_band_before_rms = _band_rms_dbfs(
                work, sample_rate=sample_rate,
                low_hz=cfg.de_esser_band_low_hz, high_hz=cfg.de_esser_band_high_hz,
            )
            work = apply_de_esser(
                work,
                sample_rate=sample_rate,
                threshold_db=cfg.de_esser_threshold_db,
                ratio=cfg.de_esser_ratio,
                max_reduction_db=cfg.de_esser_max_reduction_db,
                band_low_hz=cfg.de_esser_band_low_hz,
                band_high_hz=cfg.de_esser_band_high_hz,
                attack_ms=cfg.de_esser_attack_ms,
                release_ms=cfg.de_esser_release_ms,
                knee_db=cfg.de_esser_knee_db,
                stereo_link=cfg.de_esser_stereo_link,
            )
            sib_band_after_rms = _band_rms_dbfs(
                work, sample_rate=sample_rate,
                low_hz=cfg.de_esser_band_low_hz, high_hz=cfg.de_esser_band_high_hz,
            )
            de_esser_estimated_reduction_db = max(0.0, sib_band_before_rms - sib_band_after_rms)
            de_esser_active = True
            applied_steps.append(f"de_esser_{cfg.de_esser_threshold_db:.1f}db")
        except ValueError as exc:
            warnings.append(f"Pominięto de-esser: {exc}")

    if cfg.noise_gate_enabled:
        work = apply_noise_gate(
            work,
            cfg.noise_gate_db,
            floor_db=cfg.noise_gate_floor_db,
            attack_ms=cfg.noise_gate_attack_ms,
            release_ms=cfg.noise_gate_release_ms,
            hold_ms=cfg.noise_gate_hold_ms,
            sample_rate=sample_rate,
        )
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
    intensity, risk, risk_warnings = _assess_cleanup_intensity(cfg, applied_steps, de_esser_estimated_reduction_db)

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
        de_esser_active=de_esser_active,
        de_esser_estimated_reduction_db=de_esser_estimated_reduction_db,
        de_esser_sibilant_band_before_rms=sib_band_before_rms,
        de_esser_sibilant_band_after_rms=sib_band_after_rms,
        cleanup_intensity=intensity,
        risk_level=risk,
        risk_warnings=risk_warnings,
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


def apply_de_esser(
    audio: np.ndarray,
    *,
    sample_rate: int,
    threshold_db: float = -28.0,
    ratio: float = 3.0,
    max_reduction_db: float = 8.0,
    band_low_hz: float = 4500.0,
    band_high_hz: float = 9500.0,
    attack_ms: float = 4.0,
    release_ms: float = 90.0,
    knee_db: float = 6.0,
    stereo_link: bool = True,
    order: int = 2,
) -> np.ndarray:
    work = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
    if sample_rate <= 0:
        raise ValueError("sample_rate musi być dodatni")
    if ratio <= 1.0:
        raise ValueError("de_esser_ratio musi być > 1.0")
    if max_reduction_db <= 0.0:
        return work

    nyquist = sample_rate / 2.0
    low = float(max(1000.0, band_low_hz))
    high = float(min(band_high_hz, nyquist - 100.0))
    if high <= low:
        raise ValueError("Pasmo de-essera jest nieprawidłowe")

    mono = work.ndim == 1
    channels = work[:, None] if mono else work
    if channels.shape[0] < max(32, order * 8):
        return work

    sos = butter(int(order), [low, high], btype="bandpass", fs=float(sample_rate), output="sos")
    try:
        band = sosfiltfilt(sos, channels, axis=0)
    except ValueError:
        band = sosfilt(sos, channels, axis=0)

    detector_raw = np.max(np.abs(band), axis=1) if stereo_link else np.abs(band)
    detector = np.maximum(detector_raw, _EPS)
    over_db = 20.0 * np.log10(detector) - float(threshold_db)
    over_db = _apply_soft_knee(over_db, knee_db)
    reduction_target_db = np.clip(over_db * (1.0 - 1.0 / float(ratio)), 0.0, float(max_reduction_db))

    if reduction_target_db.ndim == 1:
        reduction_db = _smooth_series(reduction_target_db, sample_rate=sample_rate, attack_ms=attack_ms, release_ms=release_ms)
        gain = np.power(10.0, -reduction_db / 20.0)
        processed = channels - (band * (1.0 - gain[:, None]))
    else:
        reduction_db = np.vstack(
            [
                _smooth_series(reduction_target_db[:, idx], sample_rate=sample_rate, attack_ms=attack_ms, release_ms=release_ms)
                for idx in range(reduction_target_db.shape[1])
            ]
        ).T
        gain = np.power(10.0, -reduction_db / 20.0)
        processed = channels - (band * (1.0 - gain))
    return processed[:, 0] if mono else processed


def apply_noise_gate(
    audio: np.ndarray,
    threshold_db: float,
    *,
    floor_db: float = -24.0,
    attack_ms: float = 4.0,
    release_ms: float = 80.0,
    hold_ms: float = 20.0,
    sample_rate: int = 48000,
) -> np.ndarray:
    work = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
    if sample_rate <= 0:
        hard = work.copy()
        threshold = 10 ** (threshold_db / 20.0)
        hard[np.abs(hard) < threshold] = 0.0
        return hard

    mono = work.ndim == 1
    channels = work[:, None] if mono else work.copy()
    detector = np.max(np.abs(channels), axis=1)
    threshold = float(10 ** (threshold_db / 20.0))
    floor_gain = float(10 ** (-abs(floor_db) / 20.0))
    hold_samples = int(max(0.0, hold_ms) * sample_rate / 1000.0)

    gain_target = np.ones(detector.shape[0], dtype=np.float64)
    below_count = 0
    for idx, level in enumerate(detector):
        if level < threshold:
            below_count += 1
        else:
            below_count = 0
        if below_count > hold_samples:
            gain_target[idx] = floor_gain

    gain = _smooth_series(gain_target, sample_rate=sample_rate, attack_ms=attack_ms, release_ms=release_ms)
    processed = channels * gain[:, None]
    return processed[:, 0] if mono else processed


def _smooth_series(values: np.ndarray, *, sample_rate: int, attack_ms: float, release_ms: float) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0 or sample_rate <= 0:
        return array
    attack_coeff = _time_to_coeff(attack_ms, sample_rate)
    release_coeff = _time_to_coeff(release_ms, sample_rate)
    out = np.empty_like(array)
    prev = float(array[0])
    out[0] = prev
    for idx in range(1, array.shape[0]):
        cur = float(array[idx])
        coeff = attack_coeff if cur > prev else release_coeff
        prev = coeff * prev + (1.0 - coeff) * cur
        out[idx] = prev
    return out


def _apply_soft_knee(over_db: np.ndarray, knee_db: float) -> np.ndarray:
    values = np.asarray(over_db, dtype=np.float64)
    if knee_db <= 0.0:
        return np.maximum(values, 0.0)
    knee_half = knee_db / 2.0
    out = np.zeros_like(values)
    above = values >= knee_half
    out[above] = values[above]
    in_knee = (values > -knee_half) & (values < knee_half)
    out[in_knee] = ((values[in_knee] + knee_half) ** 2) / max(2.0 * knee_db, _EPS)
    return out


def _time_to_coeff(time_ms: float, sample_rate: int) -> float:
    t = max(0.1, float(time_ms)) / 1000.0
    return float(np.exp(-1.0 / (t * max(1, int(sample_rate)))))


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


def _band_rms_dbfs(
    audio: np.ndarray,
    *,
    sample_rate: int,
    low_hz: float,
    high_hz: float,
    order: int = 2,
) -> float:
    """RMS bandpass-filtered signal as dBFS. Returns -240 on silence or error."""
    work = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
    if sample_rate <= 0 or work.size == 0:
        return -240.0
    nyquist = sample_rate / 2.0
    low = float(max(1.0, low_hz))
    high = float(min(high_hz, nyquist - 100.0))
    if high <= low or work.shape[0] < max(32, order * 8):
        return -240.0
    try:
        sos = butter(int(order), [low, high], btype="bandpass", fs=float(sample_rate), output="sos")
        mono = to_mono(work)
        try:
            filtered = sosfiltfilt(sos, mono, axis=0)
        except ValueError:
            filtered = sosfilt(sos, mono, axis=0)
        rms = float(np.sqrt(np.mean(np.square(filtered))))
        return float(20.0 * np.log10(max(rms, _EPS)))
    except Exception:
        return -240.0


def _assess_cleanup_intensity(
    cfg: CleanupSettings,
    applied_steps: list[str],
    de_esser_reduction_db: float,
) -> tuple[str, str, tuple[str, ...]]:
    """Returns (intensity, risk_level, risk_warnings)."""
    score = 0
    risk_warnings: list[str] = []

    # --- intensity scoring ---
    if cfg.de_esser_enabled:
        score += 1
        if de_esser_reduction_db > 4.0:
            score += 1
            risk_warnings.append(f"de-esser aktywny — szacowana redukcja {de_esser_reduction_db:.1f} dB")
        else:
            risk_warnings.append("de-esser aktywny")

    if cfg.noise_gate_enabled:
        score += 1
        risk_warnings.append("noise gate aktywny")

    if cfg.trim_silence_enabled:
        score += 1
        risk_warnings.append("trim silence aktywny — może uciąć naturalne wybrzmienie")

    if cfg.high_pass_enabled and cfg.high_pass_hz > 100.0:
        score += 1
        risk_warnings.append(f"high-pass powyżej 100 Hz ({cfg.high_pass_hz:.0f} Hz) — sprawdź wokal basowy")

    if cfg.gain_stage_target_db is not None:
        score += 1
        risk_warnings.append(f"gain staging aktywny (target {cfg.gain_stage_target_db:.1f} dBFS)")

    # intensity label
    if score == 0:
        intensity = "none"
    elif score <= 1:
        intensity = "light"
    elif score <= 3:
        intensity = "medium"
    else:
        intensity = "strong"

    # risk label
    if score == 0:
        risk = "low"
    elif score <= 2 and not any("powyżej 100" in w or "gain staging" in w for w in risk_warnings):
        risk = "low"
    elif score <= 3:
        risk = "medium"
    else:
        risk = "high"

    return intensity, risk, tuple(risk_warnings)

