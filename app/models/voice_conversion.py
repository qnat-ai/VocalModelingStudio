from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf

from app.audio.format import ensure_audio_shape
from app.engines.applio.engine import ApplioEngine

logger = logging.getLogger(__name__)


class VoiceConversionEngine:
    """Wrapper na przyszłe modele: RVC, Seed-VC, OpenVoice, Applio.

    Bez `enabled=True` to bezpieczny no-op. Z `enabled=True` wybiera backend
    przez `config["backend"]`:

      - "applio_gradio": woła lokalnie działającą instancję Applio przez jej
        wbudowane API Gradio (zalecane, patrz docs/APPLIO_INTEGRATION_PL.md).
      - "rvc_cli": woła zewnętrzny binarny CLI (zachowane dla narzędzi, które
        faktycznie wystawiają taki interfejs; Applio go nie wystawia).
      - dowolna inna wartość / brak: no-op, audio przechodzi bez zmian.
    """

    def __init__(self, enabled: bool = False, config: dict | None = None) -> None:
        self.enabled = enabled
        self.config = config or {}

    def convert(self, audio: np.ndarray, sr: int, reference_path: Path | None = None) -> np.ndarray:
        if not self.enabled:
            return audio
        if reference_path is None:
            raise ValueError("Voice conversion wymaga próbki reference_path.")
        mode = str(self.config.get("backend", "placeholder")).lower()
        if mode == "rvc_cli":
            return self._convert_with_rvc_cli(audio, sr, reference_path)
        if mode == "applio_gradio":
            engine = ApplioEngine(config=self.config)
            return engine.convert(audio, sr, reference_path)
        return audio

    def _convert_with_rvc_cli(self, audio: np.ndarray, sr: int, reference_path: Path) -> np.ndarray:
        binary = str(self.config.get("rvc_binary", "rvc"))
        if shutil.which(binary) is None:
            if bool(self.config.get("strict", False)):
                raise RuntimeError(f"RVC binary not found in PATH: {binary}")
            return audio

        with tempfile.TemporaryDirectory(prefix="vms_rvc_") as tmp_dir:
            tmp = Path(tmp_dir)
            input_wav = tmp / "input.wav"
            output_wav = tmp / "output.wav"
            sf.write(input_wav, ensure_audio_shape(np.asarray(audio)), sr)

            command = [
                binary,
                "--input",
                str(input_wav),
                "--reference",
                str(reference_path),
                "--output",
                str(output_wav),
                "--device",
                str(self.config.get("device", "cuda")),
            ]
            completed = subprocess.run(command, capture_output=True, text=True)
            if completed.returncode != 0 or not output_wav.exists():
                if bool(self.config.get("strict", False)):
                    details = (completed.stderr or completed.stdout or "").strip()
                    raise RuntimeError(f"RVC conversion failed: {details}")
                return audio

            converted, _ = sf.read(output_wav, always_2d=False)
            return ensure_audio_shape(np.asarray(converted))

