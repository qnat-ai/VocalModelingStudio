from __future__ import annotations

import librosa
import numpy as np

from app.audio.format import to_mono


def estimate_f0_mono(audio: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray]:
    """Prosta analiza F0 przez librosa.pyin. Dla MVP wystarcza do diagnostyki."""
    mono = to_mono(audio)
    f0, voiced_flag, voiced_prob = librosa.pyin(
        mono,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C6"),
        sr=sr,
    )
    times = librosa.times_like(f0, sr=sr)
    return times, f0


def pitch_frame_to_note(f0_hz: float) -> tuple[float | None, str, float | None]:
    if not np.isfinite(f0_hz) or f0_hz <= 0.0:
        return None, "unvoiced", None
    midi = float(librosa.hz_to_midi(f0_hz))
    nearest_midi = int(round(midi))
    note_name = str(librosa.midi_to_note(nearest_midi, unicode=False))
    cents_off = float((midi - nearest_midi) * 100.0)
    return midi, note_name, cents_off


def placeholder_pitch_correction(audio: np.ndarray, sr: int, strength: float = 0.65) -> np.ndarray:
    """Miejsce na prawdziwą korekcję nut.

    W wersji MVP nie zmieniamy destrukcyjnie audio, żeby nie pogorszyć jakości.
    Docelowo tutaj można podpiąć Rubber Band, pyworld, RMVPE, algorytm melody-to-scale,
    albo wyeksportować ścieżkę do profesjonalnej korekcji w zewnętrznym programie (np. Melodyne).
    """
    _ = sr, strength
    return audio
