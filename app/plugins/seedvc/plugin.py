"""Seed-VC voice conversion plugin placeholder."""
from pathlib import Path
from app.plugins.base import BasePlugin, PluginInfo


class SeedVCPlugin(BasePlugin):
    info = PluginInfo(name="Seed-VC", version="placeholder")

    def convert(self, source: Path, reference: Path, output: Path) -> Path:
        raise NotImplementedError("Wire Seed-VC model later.")
