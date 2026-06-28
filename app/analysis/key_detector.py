"""Simple key detection using chroma templates."""
from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np

_NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
_MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.6, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def detect_key(audio_path: Path) -> str:
    audio, sr = librosa.load(audio_path, sr=None, mono=True)
    return detect_key_from_audio(audio, sr)


def detect_key_from_audio(audio: np.ndarray, sample_rate: int) -> str:
    if audio.size == 0 or sample_rate <= 0:
        return "unknown"

    chroma = librosa.feature.chroma_cqt(y=np.asarray(audio, dtype=np.float64), sr=int(sample_rate))
    chroma_mean = np.mean(chroma, axis=1)
    if not np.any(chroma_mean):
        return "unknown"

    chroma_norm = chroma_mean / np.sum(chroma_mean)
    best_score = -1.0
    best_note = 0
    best_mode = "major"

    for note in range(12):
        major_profile = np.roll(_MAJOR_PROFILE, note)
        minor_profile = np.roll(_MINOR_PROFILE, note)
        major_score = float(np.dot(chroma_norm, major_profile / np.sum(major_profile)))
        minor_score = float(np.dot(chroma_norm, minor_profile / np.sum(minor_profile)))
        if major_score > best_score:
            best_score = major_score
            best_note = note
            best_mode = "major"
        if minor_score > best_score:
            best_score = minor_score
            best_note = note
            best_mode = "minor"

    return f"{_NOTE_NAMES[best_note]} {best_mode}"

