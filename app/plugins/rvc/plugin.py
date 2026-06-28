"""RVC voice conversion plugin placeholder."""
from pathlib import Path
from app.plugins.base import BasePlugin, PluginInfo


class RVCPlugin(BasePlugin):
    info = PluginInfo(name="RVC", version="placeholder")

    def convert(self, source: Path, model_path: Path, output: Path) -> Path:
        raise NotImplementedError("Wire external RVC implementation later.")
