"""Shared helpers for internal audio array shape conventions.

Internal standard:
- mono: (samples,)
- multi-channel: (samples, channels)
"""
from __future__ import annotations

import numpy as np


MAX_REASONABLE_CHANNELS = 8


def ensure_audio_shape(audio: np.ndarray) -> np.ndarray:
    """Return audio in project-standard shape.

    Heuristics:
    - 1D arrays are treated as mono.
    - 2D arrays with a small first dimension and a much larger second dimension
      are assumed to be channel-first and are transposed.
    """
    array = np.asarray(audio)
    if array.ndim <= 1:
        return array.reshape(-1) if array.ndim == 1 else array
    if array.ndim != 2:
        return array.reshape(-1)
    if array.shape[0] <= MAX_REASONABLE_CHANNELS and array.shape[1] > array.shape[0]:
        return array.T
    return array


def to_mono(audio: np.ndarray) -> np.ndarray:
    array = ensure_audio_shape(audio)
    if array.ndim == 1:
        return array
    return np.mean(array, axis=1)


def channel_count(audio: np.ndarray) -> int:
    array = ensure_audio_shape(audio)
    if array.ndim == 1:
        return 1
    return int(array.shape[1])

