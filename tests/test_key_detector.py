from __future__ import annotations

import numpy as np

from app.analysis.key_detector import detect_key_from_audio


def test_detect_key_from_audio_returns_known_format():
    sample_rate = 22_050
    duration = 1.0
    time = np.linspace(0.0, duration, int(sample_rate * duration), endpoint=False)
    # C major triad: C4, E4, G4
    signal = (
        0.25 * np.sin(2 * np.pi * 261.63 * time)
        + 0.2 * np.sin(2 * np.pi * 329.63 * time)
        + 0.2 * np.sin(2 * np.pi * 392.00 * time)
    )

    detected = detect_key_from_audio(signal, sample_rate)

    assert isinstance(detected, str)
    assert " " in detected
    note, mode = detected.split(" ", 1)
    assert note in {"C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"}
    assert mode in {"major", "minor"}

