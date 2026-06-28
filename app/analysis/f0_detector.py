"""F0 / pitch detection abstraction.

Implementacje docelowe: RMVPE, CREPE, pyworld, librosa.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class F0Track:
    times: list[float]
    frequencies_hz: list[float]
    confidence: list[float]


class F0Detector:
    def analyze(self, audio_path: Path) -> F0Track:
        raise NotImplementedError("Podłącz RMVPE/CREPE/pyworld w kolejnej iteracji.")
