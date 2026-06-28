"""Demucs CLI plugin wrapper for vocal/instrument separation."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.plugins.base import BasePlugin, PluginInfo


class DemucsPlugin(BasePlugin):
    info = PluginInfo(
        name="demucs",
        version="1.0",
        enabled=True,
        notes="Uses external demucs CLI to split stems.",
    )

    def __init__(self, binary_name: str = "demucs") -> None:
        self.binary_name = binary_name

    def check_available(self) -> bool:
        return shutil.which(self.binary_name) is not None

    def separate_vocals(
        self,
        input_path: Path,
        output_dir: Path,
        *,
        model_name: str = "htdemucs",
        two_stems: str = "vocals",
    ) -> Path:
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        if not self.check_available():
            raise RuntimeError("Demucs CLI is not available in PATH.")

        output_dir.mkdir(parents=True, exist_ok=True)
        command = [
            self.binary_name,
            "--two-stems",
            two_stems,
            "-n",
            model_name,
            "-o",
            str(output_dir),
            str(input_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            details = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(f"Demucs separation failed: {details}")

        candidates = sorted(output_dir.rglob("vocals.wav"))
        if not candidates:
            raise RuntimeError("Demucs finished, but vocals stem was not found.")
        return candidates[-1]
