"""Discrete mastering stages used by the mastering chain."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import butter, sosfiltfilt

from app.audio.format import ensure_audio_shape
from app.mastering.meters import measure_peak


@dataclass(frozen=True)
class GainStage:
    gain_db: float = 0.0

    def process(self, audio: np.ndarray) -> np.ndarray:
        array = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
        if self.gain_db == 0.0:
            return array
        return array * 10 ** (self.gain_db / 20.0)


@dataclass(frozen=True)
class HighPassFilterStage:
    enabled: bool = True
    cutoff_hz: float = 80.0

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        array = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
        if not self.enabled or sample_rate <= 0 or self.cutoff_hz <= 0 or array.shape[0] < 9:
            return array
        nyquist = sample_rate / 2.0
        normalized_cutoff = min(max(self.cutoff_hz / nyquist, 1e-5), 0.99)
        sos = butter(2, normalized_cutoff, btype="highpass", output="sos")
        try:
            return sosfiltfilt(sos, array, axis=0)
        except ValueError:
            return array


@dataclass(frozen=True)
class CompressorStage:
    threshold_db: float = -18.0
    ratio: float = 2.0

    def process(self, audio: np.ndarray) -> np.ndarray:
        array = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
        if self.ratio <= 1.0:
            return array
        threshold = 10 ** (self.threshold_db / 20.0)
        magnitude = np.abs(array)
        compressed = magnitude.copy()
        over_threshold = magnitude > threshold
        compressed[over_threshold] = threshold + (magnitude[over_threshold] - threshold) / self.ratio
        return np.sign(array) * compressed


@dataclass(frozen=True)
class LimiterStage:
    ceiling_db: float = -1.0

    def process(self, audio: np.ndarray) -> np.ndarray:
        array = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
        ceiling = 10 ** (self.ceiling_db / 20.0)
        peak = measure_peak(array)
        if peak > ceiling and peak > 0.0:
            array = array * (ceiling / peak)
        return array


@dataclass(frozen=True)
class DeEsserPlaceholderStage:
    enabled: bool = False

    def process(self, audio: np.ndarray) -> np.ndarray:
        return ensure_audio_shape(np.asarray(audio, dtype=np.float64))


@dataclass(frozen=True)
class AirStage:
    amount: float = 0.0
    cutoff_hz: float = 9000.0

    def process(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        array = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
        if self.amount <= 0.0:
            return array
        high_band = HighPassFilterStage(enabled=True, cutoff_hz=self.cutoff_hz).process(array, sample_rate)
        mixed = array + high_band * float(np.clip(self.amount, 0.0, 2.0))
        return np.clip(mixed, -1.0, 1.0)


@dataclass(frozen=True)
class StereoWidthStage:
    width: float = 1.0

    def process(self, audio: np.ndarray) -> np.ndarray:
        array = ensure_audio_shape(np.asarray(audio, dtype=np.float64))
        if array.ndim != 2 or array.shape[1] < 2 or self.width == 1.0:
            return array
        width = float(np.clip(self.width, 0.0, 2.0))
        left = array[:, 0]
        right = array[:, 1]
        mid = (left + right) * 0.5
        side = (left - right) * 0.5 * width
        widened = np.column_stack((mid + side, mid - side))
        return np.clip(widened, -1.0, 1.0)

