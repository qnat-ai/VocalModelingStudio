"""High-level voice modeling engine."""
from pathlib import Path


class VoiceModelingEngine:
    def convert(self, source_vocal: Path, reference_voice: Path, output_path: Path) -> Path:
        raise NotImplementedError("Podłącz Seed-VC albo RVC w pluginach.")
