"""Export manager for WAV/MIDI/reports."""
from pathlib import Path


class ExportManager:
    def export_wav(self, source: Path, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        if source != target:
            target.write_bytes(source.read_bytes())
        return target
