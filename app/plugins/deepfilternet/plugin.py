"""DeepFilterNet denoise plugin placeholder."""
from pathlib import Path
from app.plugins.base import BasePlugin, PluginInfo


class DeepFilterNetPlugin(BasePlugin):
    info = PluginInfo(name="DeepFilterNet", version="placeholder")

    def denoise(self, input_path: Path, output_path: Path) -> Path:
        raise NotImplementedError("Install and wire DeepFilterNet in a later iteration.")
