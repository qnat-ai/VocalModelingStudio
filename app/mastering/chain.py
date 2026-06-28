"""Lightweight vocal mastering chain."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from app.audio.format import ensure_audio_shape
from app.mastering.meters import measure_crest_factor_db, measure_rms_dbfs
from app.mastering.presets import neutral_mastering_preset
from app.mastering.stages import (
    AirStage,
    CompressorStage,
    DeEsserPlaceholderStage,
    GainStage,
    HighPassFilterStage,
    LimiterStage,
    StereoWidthStage,
)


@dataclass(frozen=True)
class MasteringSettings:
    enable_highpass: bool = True
    highpass_hz: float = 80.0
    compressor_threshold_db: float = -18.0
    compressor_ratio: float = 2.0
    limiter_ceiling_db: float = -1.0
    makeup_gain_db: float = 0.0
    adaptive_enabled: bool = False
    adaptive_target_rms_dbfs: float = -18.0
    adaptive_min_ratio: float = 1.4
    adaptive_max_ratio: float = 3.5
    adaptive_max_makeup_db: float = 6.0
    air_amount: float = 0.0
    air_cutoff_hz: float = 9000.0
    stereo_width: float = 1.0
    deesser_enabled: bool = False

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None = None) -> "MasteringSettings":
        data = data or {}
        return cls(
            enable_highpass=bool(data.get("enable_highpass", True)),
            highpass_hz=float(data.get("highpass_hz", 80.0)),
            compressor_threshold_db=float(data.get("compressor_threshold_db", -18.0)),
            compressor_ratio=float(data.get("compressor_ratio", 2.0)),
            limiter_ceiling_db=float(data.get("limiter_ceiling_db", -1.0)),
            makeup_gain_db=float(data.get("makeup_gain_db", 0.0)),
            adaptive_enabled=bool(data.get("adaptive_enabled", False)),
            adaptive_target_rms_dbfs=float(data.get("adaptive_target_rms_dbfs", -18.0)),
            adaptive_min_ratio=float(data.get("adaptive_min_ratio", 1.4)),
            adaptive_max_ratio=float(data.get("adaptive_max_ratio", 3.5)),
            adaptive_max_makeup_db=float(data.get("adaptive_max_makeup_db", 6.0)),
            air_amount=float(data.get("air_amount", 0.0)),
            air_cutoff_hz=float(data.get("air_cutoff_hz", 9000.0)),
            stereo_width=float(data.get("stereo_width", 1.0)),
            deesser_enabled=bool(data.get("deesser_enabled", False)),
        )

    @classmethod
    def neutral_preset(cls, overrides: dict[str, Any] | None = None) -> "MasteringSettings":
        return cls.from_mapping(neutral_mastering_preset(overrides))


class MasteringChain:
    def __init__(self, settings: MasteringSettings | None = None) -> None:
        self.settings = settings or MasteringSettings()
        self._last_profile: dict[str, float | bool | list[str]] = {}

    @classmethod
    def from_config(cls, config: dict[str, Any] | None = None) -> "MasteringChain":
        return cls(MasteringSettings.from_mapping(config))

    def process_audio(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        array = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
        if array.size == 0:
            return array

        original_ndim = array.ndim
        work = array[:, None] if original_ndim == 1 else array.copy()

        work = HighPassFilterStage(enabled=self.settings.enable_highpass, cutoff_hz=self.settings.highpass_hz).process(
            work,
            sample_rate,
        )

        threshold_db = self.settings.compressor_threshold_db
        ratio = self.settings.compressor_ratio
        makeup_gain_db = self.settings.makeup_gain_db
        adaptive_profile: dict[str, float | bool] = {"adaptive_enabled": self.settings.adaptive_enabled}
        if self.settings.adaptive_enabled:
            adaptive_profile = self._derive_adaptive_profile(work)
            threshold_db = float(adaptive_profile["compressor_threshold_db"])
            ratio = float(adaptive_profile["compressor_ratio"])
            makeup_gain_db = float(adaptive_profile["makeup_gain_db"])

        work = CompressorStage(threshold_db=threshold_db, ratio=ratio).process(work)
        work = GainStage(gain_db=makeup_gain_db).process(work)
        work = DeEsserPlaceholderStage(enabled=self.settings.deesser_enabled).process(work)
        work = AirStage(amount=self.settings.air_amount, cutoff_hz=self.settings.air_cutoff_hz).process(work, sample_rate)
        work = StereoWidthStage(width=self.settings.stereo_width).process(work)
        work = LimiterStage(ceiling_db=self.settings.limiter_ceiling_db).process(work)

        self._last_profile = {
            **adaptive_profile,
            "compressor_threshold_db": float(threshold_db),
            "compressor_ratio": float(ratio),
            "makeup_gain_db": float(makeup_gain_db),
            "limiter_ceiling_db": float(self.settings.limiter_ceiling_db),
            "air_amount": float(self.settings.air_amount),
            "stereo_width": float(self.settings.stereo_width),
            "deesser_enabled": bool(self.settings.deesser_enabled),
            "chain_stages": [
                "highpass",
                "compressor",
                "gain_stage",
                "deesser_placeholder",
                "air",
                "stereo_width",
                "limiter",
            ],
        }
        return work[:, 0] if original_ndim == 1 else work

    def get_last_profile(self) -> dict[str, float | bool | list[str]]:
        return dict(self._last_profile)

    def process(self, input_path: Path, output_path: Path) -> Path:
        audio, sr = sf.read(input_path, always_2d=False)
        processed = self.process_audio(ensure_audio_shape(np.asarray(audio)), int(sr))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(output_path, processed, sr)
        return output_path

    def _derive_adaptive_profile(self, audio: np.ndarray) -> dict[str, float | bool]:
        rms_dbfs = measure_rms_dbfs(audio)
        crest_factor_db = measure_crest_factor_db(audio)

        target = self.settings.adaptive_target_rms_dbfs
        threshold_db = float(np.clip(
            self.settings.compressor_threshold_db + (rms_dbfs - target) * 0.35,
            -30.0,
            -8.0,
        ))

        ratio = self.settings.compressor_ratio
        if crest_factor_db < 6.0:
            ratio -= 0.4
        elif crest_factor_db > 12.0:
            ratio += 0.4
        ratio = float(np.clip(ratio, self.settings.adaptive_min_ratio, self.settings.adaptive_max_ratio))

        delta_to_target = target - rms_dbfs
        makeup_gain_db = self.settings.makeup_gain_db + max(0.0, delta_to_target * 0.5)
        makeup_gain_db = float(np.clip(makeup_gain_db, 0.0, self.settings.adaptive_max_makeup_db))

        return {
            "adaptive_enabled": True,
            "input_rms_dbfs": rms_dbfs,
            "input_crest_factor_db": crest_factor_db,
            "compressor_threshold_db": threshold_db,
            "compressor_ratio": ratio,
            "makeup_gain_db": makeup_gain_db,
        }
