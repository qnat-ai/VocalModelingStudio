"""RMVPE pitch extraction plugin placeholder."""
from pathlib import Path
from app.plugins.base import BasePlugin, PluginInfo


class RMVPEPlugin(BasePlugin):
    info = PluginInfo(name="RMVPE", version="placeholder")

    def extract_f0(self, audio_path: Path):
        raise NotImplementedError("Wire RMVPE later.")
