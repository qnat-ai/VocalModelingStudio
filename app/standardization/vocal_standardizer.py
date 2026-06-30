"""Vocal standardization against an instrumental reference.

Project rule for this module:
- the instrumental is a reference only and is never modified destructively;
- the main render is always the processed vocal file;
- preview_mix.wav is only a listening/checking helper.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import librosa
import numpy as np
import soundfile as sf
from app.audio.cleanup import CleanupReport, CleanupSettings, process_cleanup_with_report

StandardizationAction = Literal["accept", "correct", "try_again"]

_EPS = 1e-12
_AUDIO_SUFFIXES = {".wav", ".flac", ".ogg", ".aiff", ".aif", ".mp3", ".m4a"}


@dataclass(frozen=True)
class TrackMetrics:
    source: str
    sample_rate: int
    channels: int
    duration_sec: float
    peak: float
    peak_dbfs: float
    rms: float
    rms_dbfs: float
    headroom_db: float
    clipping: bool
    clipped_samples: int
    crest_factor_db: float
    low_band_ratio: float
    presence_band_ratio: float
    sibilance_band_ratio: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StandardizationRecommendation:
    mode: str
    proposed_vocal_gain_db: float
    alternative_vocal_gain_db: float
    target_vocal_relative_to_instrumental_db: float | None
    summary: str
    issues: tuple[str, ...] = ()
    suggestions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StandardizationReport:
    vocal_metrics_before: TrackMetrics
    vocal_metrics_after: TrackMetrics | None
    instrumental_metrics: TrackMetrics | None
    recommendation: StandardizationRecommendation
    applied_vocal_gain_db: float | None
    output_vocal_path: str | None
    preview_mix_path: str | None
    report_path: str | None
    created_at: str
    cleanup_report: CleanupReport | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def to_text(self) -> str:
        lines = [
            "VocalModelingStudio — raport standaryzacji wokalu",
            f"Utworzono: {self.created_at}",
            "",
            "Zasada: instrumental jest referencją; VMS nie modyfikuje instrumentalu destrukcyjnie.",
            "Główny wynik: vocal_processed.wav. Preview mix służy tylko do odsłuchu kontrolnego.",
            "",
            "Rekomendacja:",
            f"- {self.recommendation.summary}",
            f"- Proponowany gain wokalu: {self.recommendation.proposed_vocal_gain_db:+.2f} dB",
            f"- Alternatywny gain wokalu: {self.recommendation.alternative_vocal_gain_db:+.2f} dB",
        ]
        if self.applied_vocal_gain_db is not None:
            lines.append(f"- Zastosowany gain wokalu: {self.applied_vocal_gain_db:+.2f} dB")
        if self.recommendation.issues:
            lines.extend(["", "Wykryte problemy:"])
            lines.extend(f"- {issue}" for issue in self.recommendation.issues)
        if self.recommendation.suggestions:
            lines.extend(["", "Sugestie:"])
            lines.extend(f"- {suggestion}" for suggestion in self.recommendation.suggestions)
        if self.cleanup_report:
            lines.extend(["", *self.cleanup_report.to_text_lines()])

        lines.extend(
            [
                "",
                "Metryki wokalu przed:",
                _metrics_line(self.vocal_metrics_before),
            ]
        )
        if self.vocal_metrics_after:
            lines.extend(["", "Metryki wokalu po:", _metrics_line(self.vocal_metrics_after)])
        if self.instrumental_metrics:
            lines.extend(["", "Metryki instrumentalu / referencji:", _metrics_line(self.instrumental_metrics)])
        if self.output_vocal_path:
            lines.extend(["", f"Wynik wokalu: {self.output_vocal_path}"])
        if self.preview_mix_path:
            lines.append(f"Preview mix: {self.preview_mix_path}")
        if self.report_path:
            lines.append(f"Raport JSON: {self.report_path}")
        if self.notes:
            lines.extend(["", "Uwagi:"])
            lines.extend(f"- {note}" for note in self.notes)
        return "\n".join(lines)


@dataclass(frozen=True)
class StandardizationResult:
    vocal_path: Path | None
    preview_mix_path: Path | None
    report_path: Path
    report_text_path: Path
    report: StandardizationReport


class VocalInstrumentalStandardizer:
    """Prepare a vocal track against an optional instrumental reference.

    This class intentionally does not behave like a DAW. It returns a processed
    vocal track and uses the instrumental only to calculate a practical gain
    recommendation and a temporary preview mix.
    """

    def __init__(
        self,
        *,
        sample_rate: int = 48000,
        output_dir: str | Path = "data/output/standardized",
        target_vocal_relative_to_instrumental_db: float = -6.0,
        max_gain_correction_db: float = 12.0,
        no_instrumental_target_peak_dbfs: float = -1.0,
        preview_mix_peak_dbfs: float = -1.0,
        cleanup_settings: CleanupSettings | None = None,
    ) -> None:
        self.sample_rate = int(sample_rate)
        self.output_dir = Path(output_dir)
        self.target_vocal_relative_to_instrumental_db = float(target_vocal_relative_to_instrumental_db)
        self.max_gain_correction_db = abs(float(max_gain_correction_db))
        self.no_instrumental_target_peak_dbfs = float(no_instrumental_target_peak_dbfs)
        self.preview_mix_peak_dbfs = float(preview_mix_peak_dbfs)
        self.cleanup_settings = cleanup_settings or CleanupSettings()

    def analyze(
        self,
        *,
        vocal_path: str | Path,
        instrumental_path: str | Path | None = None,
    ) -> StandardizationReport:
        vocal_audio, sr = self._load_audio(Path(vocal_path))
        instrumental_audio = None
        if instrumental_path:
            instrumental_audio, _ = self._load_audio(Path(instrumental_path))

        return self._build_report(
            vocal_path=Path(vocal_path),
            vocal_audio=vocal_audio,
            instrumental_path=Path(instrumental_path) if instrumental_path else None,
            instrumental_audio=instrumental_audio,
            sr=sr,
            applied_gain_db=None,
            output_vocal_path=None,
            preview_mix_path=None,
            report_path=None,
            cleanup_report=None,
        )

    def render(
        self,
        *,
        vocal_path: str | Path,
        instrumental_path: str | Path | None = None,
        action: StandardizationAction = "accept",
        manual_gain_db: float | None = None,
        session_name: str | None = None,
    ) -> StandardizationResult:
        vocal_path = Path(vocal_path)
        instrumental_path_obj = Path(instrumental_path) if instrumental_path else None

        vocal_audio, sr = self._load_audio(vocal_path)
        instrumental_audio = None
        if instrumental_path_obj:
            instrumental_audio, _ = self._load_audio(instrumental_path_obj)

        proposal_report = self._build_report(
            vocal_path=vocal_path,
            vocal_audio=vocal_audio,
            instrumental_path=instrumental_path_obj,
            instrumental_audio=instrumental_audio,
            sr=sr,
            applied_gain_db=None,
            output_vocal_path=None,
            preview_mix_path=None,
            report_path=None,
        )
        gain_db = self._choose_gain(
            proposal_report.recommendation,
            action=action,
            manual_gain_db=manual_gain_db,
        )

        output_session_dir = self._session_dir(vocal_path=vocal_path, session_name=session_name)
        output_session_dir.mkdir(parents=True, exist_ok=True)

        cleaned_vocal, cleanup_report = process_cleanup_with_report(vocal_audio, sr, self.cleanup_settings)

        adjusted_vocal = apply_gain_db(cleaned_vocal, gain_db)
        adjusted_vocal = limit_peak(adjusted_vocal, dbfs=-1.0)
        output_vocal_path = output_session_dir / "vocal_processed.wav"
        self._save_audio(output_vocal_path, adjusted_vocal, sr)

        preview_mix_path: Path | None = None
        if instrumental_audio is not None:
            # Tworzymy mix kontrolny
            preview_mix = build_preview_mix(adjusted_vocal, instrumental_audio)
            preview_mix = limit_peak(preview_mix, dbfs=self.preview_mix_peak_dbfs)
            
            # Wytnij fragment 20s wokół najgłośniejszego momentu wokalu dla szybkiej weryfikacji
            preview_mix_short = self._extract_representative_segment(preview_mix, adjusted_vocal, sr, duration_sec=20.0)
            
            preview_mix_path = output_session_dir / "preview_mix.wav"
            self._save_audio(preview_mix_path, preview_mix_short, sr)

        report_path = output_session_dir / "vocal_standardization_report.json"
        final_report = self._build_report(
            vocal_path=vocal_path,
            vocal_audio=vocal_audio,
            instrumental_path=instrumental_path_obj,
            instrumental_audio=instrumental_audio,
            sr=sr,
            applied_gain_db=gain_db,
            output_vocal_path=output_vocal_path,
            preview_mix_path=preview_mix_path,
            report_path=report_path,
            vocal_audio_after=adjusted_vocal,
            cleanup_report=cleanup_report,
        )
        report_path.write_text(final_report.to_json(), encoding="utf-8")
        report_text_path = output_session_dir / "vocal_standardization_report.txt"
        report_text_path.write_text(final_report.to_text(), encoding="utf-8")

        return StandardizationResult(
            vocal_path=output_vocal_path,
            preview_mix_path=preview_mix_path,
            report_path=report_path,
            report_text_path=report_text_path,
            report=final_report,
        )

    def _build_report(
        self,
        *,
        vocal_path: Path,
        vocal_audio: np.ndarray,
        instrumental_path: Path | None,
        instrumental_audio: np.ndarray | None,
        sr: int,
        applied_gain_db: float | None,
        output_vocal_path: Path | None,
        preview_mix_path: Path | None,
        report_path: Path | None,
        vocal_audio_after: np.ndarray | None = None,
        cleanup_report: CleanupReport | None = None,
    ) -> StandardizationReport:
        vocal_metrics = analyze_track(vocal_audio, sr, source=str(vocal_path))
        instrumental_metrics = (
            analyze_track(instrumental_audio, sr, source=str(instrumental_path))
            if instrumental_audio is not None and instrumental_path is not None
            else None
        )
        vocal_metrics_after = analyze_track(vocal_audio_after, sr, source=str(output_vocal_path)) if vocal_audio_after is not None and output_vocal_path else None
        recommendation = self._recommend(vocal_metrics, instrumental_metrics)
        notes = (
            "Instrumental służy wyłącznie jako referencja do dopasowania wokalu.",
            "preview_mix.wav nie jest produktem końcowym — użyj go tylko do kontroli odsłuchowej.",
        )
        return StandardizationReport(
            vocal_metrics_before=vocal_metrics,
            vocal_metrics_after=vocal_metrics_after,
            instrumental_metrics=instrumental_metrics,
            recommendation=recommendation,
            applied_vocal_gain_db=applied_gain_db,
            output_vocal_path=str(output_vocal_path) if output_vocal_path else None,
            preview_mix_path=str(preview_mix_path) if preview_mix_path else None,
            report_path=str(report_path) if report_path else None,
            created_at=datetime.now().isoformat(timespec="seconds"),
            cleanup_report=cleanup_report,
            notes=notes,
        )

    def _recommend(
        self,
        vocal_metrics: TrackMetrics,
        instrumental_metrics: TrackMetrics | None,
    ) -> StandardizationRecommendation:
        issues: list[str] = []
        suggestions: list[str] = []
        target_relative = None

        if vocal_metrics.clipping:
            issues.append("Ścieżka wokalna zawiera clipping — przed dalszą obróbką obniż gain lub użyj bezpieczniejszego źródła.")
        if vocal_metrics.headroom_db < 1.0:
            suggestions.append("Zostaw minimum około 1 dB headroomu dla przetworzonego wokalu.")
        if vocal_metrics.low_band_ratio > 0.30:
            suggestions.append("Wokal ma dużo energii w niskim paśmie; rozważ high-pass ok. 70–120 Hz.")
        if vocal_metrics.sibilance_band_ratio > 0.22:
            suggestions.append("Wokal ma wyraźną energię w zakresie sybilantów; rozważ de-esser.")

        if instrumental_metrics is None:
            gain = gain_to_target_peak(vocal_metrics.peak_dbfs, self.no_instrumental_target_peak_dbfs)
            gain = clamp(gain, -self.max_gain_correction_db, self.max_gain_correction_db)
            summary = "Brak instrumentalu: zaproponowano bezpieczne wyrównanie ścieżki wokalnej do docelowego peaku."
            if abs(gain) > 6.0:
                issues.append("Korekta gain przekracza 6 dB; sprawdź, czy źródło nie jest zbyt ciche albo zbyt głośne.")
            return StandardizationRecommendation(
                mode="vocal_only",
                proposed_vocal_gain_db=float(gain),
                alternative_vocal_gain_db=float(gain * 0.75),
                target_vocal_relative_to_instrumental_db=None,
                summary=summary,
                issues=tuple(issues),
                suggestions=tuple(suggestions),
            )

        target_relative = self.target_vocal_relative_to_instrumental_db
        desired_vocal_rms_dbfs = instrumental_metrics.rms_dbfs + target_relative
        gain = desired_vocal_rms_dbfs - vocal_metrics.rms_dbfs
        gain = clamp(gain, -self.max_gain_correction_db, self.max_gain_correction_db)
        gain = avoid_peak_clipping(vocal_metrics.peak_dbfs, gain, ceiling_dbfs=-1.0)
        alternative_gain = clamp(gain * 0.75, -self.max_gain_correction_db, self.max_gain_correction_db)

        if abs(gain) < 0.75:
            summary = "Poziom wokalu jest technicznie blisko referencji; zaproponowano minimalną korektę."
        elif gain > 0:
            summary = f"Wokal jest za cichy względem instrumentalu; zaproponowano podbicie o {gain:.2f} dB."
        else:
            summary = f"Wokal jest za głośny względem instrumentalu; zaproponowano obniżenie o {abs(gain):.2f} dB."

        if instrumental_metrics.presence_band_ratio > 0.24 and vocal_metrics.presence_band_ratio < instrumental_metrics.presence_band_ratio:
            issues.append("Możliwe maskowanie wokalu: instrumental ma dużą energię w paśmie obecności 1–4 kHz.")
            suggestions.append("Rozważ delikatne EQ w DAW: miejsce dla wokalu w paśmie ok. 1–4 kHz albo lekkie podbicie obecności wokalu.")
        if instrumental_metrics.rms_dbfs > -10.0:
            issues.append("Instrumental jest bardzo głośny jako referencja; automatyczne dopasowanie wokalu może wymagać kontroli w DAW.")
        if abs(gain) >= self.max_gain_correction_db - 0.01:
            issues.append("Korekta gain została ograniczona limitem bezpieczeństwa; sprawdź poziomy źródłowe.")

        return StandardizationRecommendation(
            mode="vocal_against_instrumental",
            proposed_vocal_gain_db=float(gain),
            alternative_vocal_gain_db=float(alternative_gain),
            target_vocal_relative_to_instrumental_db=float(target_relative),
            summary=summary,
            issues=tuple(issues),
            suggestions=tuple(suggestions),
        )

    def _choose_gain(
        self,
        recommendation: StandardizationRecommendation,
        *,
        action: StandardizationAction,
        manual_gain_db: float | None,
    ) -> float:
        if action == "correct":
            if manual_gain_db is None:
                raise ValueError("manual_gain_db is required for action='correct'.")
            return float(clamp(float(manual_gain_db), -self.max_gain_correction_db, self.max_gain_correction_db))
        if action == "try_again":
            return float(recommendation.alternative_vocal_gain_db)
        return float(recommendation.proposed_vocal_gain_db)

    def _session_dir(self, *, vocal_path: Path, session_name: str | None) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = sanitize_filename(session_name or vocal_path.stem or "vocal")
        return self.output_dir / f"{stamp}_{base}"

    def _load_audio(self, path: Path) -> tuple[np.ndarray, int]:
        if not path.exists():
            raise FileNotFoundError(f"Nie znaleziono pliku audio: {path}")
        if path.suffix.lower() not in _AUDIO_SUFFIXES:
            raise ValueError(f"Nieobsługiwany format audio: {path.suffix}")
        audio, sr = librosa.load(path, sr=self.sample_rate, mono=False)
        return np.asarray(audio, dtype=np.float64), int(sr)

    def _save_audio(self, path: Path, audio: np.ndarray, sr: int) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(path, to_samples_channels(audio), int(sr))

    def _extract_representative_segment(
        self,
        full_mix: np.ndarray,
        vocal_ref: np.ndarray,
        sr: int,
        duration_sec: float = 20.0,
    ) -> np.ndarray:
        """Wytnij fragment wokół najgłośniejszego momentu wokalu dla weryfikacji."""
        samples_channels = to_samples_channels(vocal_ref)
        mono_v = np.mean(samples_channels, axis=1) if samples_channels.ndim == 2 else samples_channels
        
        # Znajdź najgłośniejszy fragment (RMS) wokalu
        win_len = int(sr * 1.0)  # 1s okno
        if mono_v.size < win_len:
            return full_mix
            
        rms_env = np.sqrt(np.convolve(np.square(mono_v), np.ones(win_len)/win_len, mode='valid'))
        max_idx = int(np.argmax(rms_env))
        
        center_sample = max_idx + (win_len // 2)
        half_dur = int((duration_sec * sr) / 2)
        
        start = max(0, center_sample - half_dur)
        end = min(full_mix.shape[1] if full_mix.ndim == 2 and full_mix.shape[0] <= 8 else full_mix.shape[0], start + int(duration_sec * sr))
        
        # Obsługa różnych układów osi (channels x samples vs samples x channels)
        if full_mix.ndim == 2:
            if full_mix.shape[0] <= 8: # channels x samples (librosa style)
                return full_mix[:, start:end]
            else: # samples x channels (soundfile style)
                return full_mix[start:end, :]
        return full_mix[start:end]


def analyze_track(audio: np.ndarray, sample_rate: int, *, source: str = "") -> TrackMetrics:
    samples_channels = to_samples_channels(audio)
    mono = np.mean(samples_channels, axis=1) if samples_channels.ndim == 2 else samples_channels
    if mono.size == 0:
        return TrackMetrics(
            source=source,
            sample_rate=int(sample_rate),
            channels=0,
            duration_sec=0.0,
            peak=0.0,
            peak_dbfs=-240.0,
            rms=0.0,
            rms_dbfs=-240.0,
            headroom_db=0.0,
            clipping=False,
            clipped_samples=0,
            crest_factor_db=0.0,
            low_band_ratio=0.0,
            presence_band_ratio=0.0,
            sibilance_band_ratio=0.0,
        )

    peak = float(np.max(np.abs(samples_channels)))
    rms = float(np.sqrt(np.mean(np.square(samples_channels))))
    peak_dbfs = linear_to_dbfs(peak)
    rms_dbfs = linear_to_dbfs(rms)
    headroom_db = max(0.0, -peak_dbfs)
    clipped_samples = int(np.count_nonzero(np.abs(samples_channels) >= 0.999))
    clipping = clipped_samples > 0
    crest_factor_db = float(peak_dbfs - rms_dbfs) if peak > 0 and rms > 0 else 0.0
    low_ratio, presence_ratio, sibilance_ratio = spectral_band_ratios(mono, sample_rate)
    channels = int(samples_channels.shape[1]) if samples_channels.ndim == 2 else 1
    duration_sec = float(samples_channels.shape[0] / sample_rate) if sample_rate else 0.0
    return TrackMetrics(
        source=source,
        sample_rate=int(sample_rate),
        channels=channels,
        duration_sec=duration_sec,
        peak=peak,
        peak_dbfs=peak_dbfs,
        rms=rms,
        rms_dbfs=rms_dbfs,
        headroom_db=headroom_db,
        clipping=clipping,
        clipped_samples=clipped_samples,
        crest_factor_db=crest_factor_db,
        low_band_ratio=low_ratio,
        presence_band_ratio=presence_ratio,
        sibilance_band_ratio=sibilance_ratio,
    )


def to_samples_channels(audio: np.ndarray) -> np.ndarray:
    array = np.asarray(audio, dtype=np.float64)
    if array.ndim == 1:
        return array
    if array.ndim != 2:
        return array.reshape(-1)
    # librosa with mono=False returns channels x samples. soundfile often uses samples x channels.
    if array.shape[0] <= 8 and array.shape[1] > array.shape[0]:
        return array.T
    return array


def from_samples_channels_like(samples_channels: np.ndarray, reference: np.ndarray) -> np.ndarray:
    ref = np.asarray(reference)
    if ref.ndim == 2 and ref.shape[0] <= 8 and ref.shape[1] > ref.shape[0]:
        return samples_channels.T
    return samples_channels


def apply_gain_db(audio: np.ndarray, gain_db: float) -> np.ndarray:
    return np.asarray(audio, dtype=np.float64) * db_to_linear(gain_db)


def limit_peak(audio: np.ndarray, *, dbfs: float = -1.0) -> np.ndarray:
    array = np.asarray(audio, dtype=np.float64)
    peak = float(np.max(np.abs(array))) if array.size else 0.0
    target = db_to_linear(dbfs)
    if peak <= 0 or peak <= target:
        return array
    return array * (target / peak)


def build_preview_mix(vocal_audio: np.ndarray, instrumental_audio: np.ndarray) -> np.ndarray:
    vocal_sc = ensure_2d(to_samples_channels(vocal_audio))
    inst_sc = ensure_2d(to_samples_channels(instrumental_audio))
    channels = max(vocal_sc.shape[1], inst_sc.shape[1])
    vocal_sc = match_channels(vocal_sc, channels)
    inst_sc = match_channels(inst_sc, channels)
    length = max(vocal_sc.shape[0], inst_sc.shape[0])
    vocal_sc = pad_or_trim(vocal_sc, length)
    inst_sc = pad_or_trim(inst_sc, length)
    return inst_sc + vocal_sc


def ensure_2d(audio: np.ndarray) -> np.ndarray:
    array = np.asarray(audio, dtype=np.float64)
    if array.ndim == 1:
        return array[:, None]
    return array


def match_channels(audio: np.ndarray, channels: int) -> np.ndarray:
    if audio.shape[1] == channels:
        return audio
    if audio.shape[1] == 1:
        return np.repeat(audio, channels, axis=1)
    return audio[:, :channels]


def pad_or_trim(audio: np.ndarray, length: int) -> np.ndarray:
    if audio.shape[0] == length:
        return audio
    if audio.shape[0] > length:
        return audio[:length]
    pad = np.zeros((length - audio.shape[0], audio.shape[1]), dtype=audio.dtype)
    return np.vstack([audio, pad])


def spectral_band_ratios(mono: np.ndarray, sample_rate: int) -> tuple[float, float, float]:
    mono = np.asarray(mono, dtype=np.float64)
    if mono.size < 16 or sample_rate <= 0:
        return 0.0, 0.0, 0.0
    window = mono[: min(mono.size, int(sample_rate * 12.0))]
    spectrum = np.abs(np.fft.rfft(window)) ** 2
    if spectrum.size == 0:
        return 0.0, 0.0, 0.0
    freqs = np.fft.rfftfreq(window.size, d=1.0 / sample_rate)
    total = float(np.sum(spectrum)) + _EPS

    def ratio(lo: float, hi: float) -> float:
        mask = (freqs >= lo) & (freqs < hi)
        return float(np.sum(spectrum[mask]) / total) if np.any(mask) else 0.0

    return ratio(20.0, 150.0), ratio(1000.0, 4000.0), ratio(5000.0, 9000.0)


def gain_to_target_peak(current_peak_dbfs: float, target_peak_dbfs: float) -> float:
    if current_peak_dbfs <= -200.0:
        return 0.0
    return float(target_peak_dbfs - current_peak_dbfs)


def avoid_peak_clipping(current_peak_dbfs: float, gain_db: float, *, ceiling_dbfs: float = -1.0) -> float:
    projected_peak = current_peak_dbfs + gain_db
    if projected_peak <= ceiling_dbfs:
        return gain_db
    return gain_db - (projected_peak - ceiling_dbfs)


def linear_to_dbfs(value: float) -> float:
    return float(20.0 * math.log10(max(float(value), _EPS)))


def db_to_linear(db_value: float) -> float:
    return float(10.0 ** (float(db_value) / 20.0))


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))


def sanitize_filename(value: str) -> str:
    allowed = []
    for char in value:
        if char.isalnum() or char in {"-", "_"}:
            allowed.append(char)
        elif char in {" ", "."}:
            allowed.append("_")
    cleaned = "".join(allowed).strip("._-")
    return cleaned or "vocal"


def _metrics_line(metrics: TrackMetrics) -> str:
    return (
        f"peak={metrics.peak_dbfs:.2f} dBFS, "
        f"rms={metrics.rms_dbfs:.2f} dBFS, "
        f"headroom={metrics.headroom_db:.2f} dB, "
        f"crest={metrics.crest_factor_db:.2f} dB, "
        f"clipping={'tak' if metrics.clipping else 'nie'}"
    )
