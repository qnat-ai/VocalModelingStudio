"""Plugin registry."""
from __future__ import annotations

from app.plugins.base import BasePlugin


class PluginManager:
    def __init__(self) -> None:
        self.plugins: list[BasePlugin] = []

    def register(self, plugin: BasePlugin) -> None:
        self.plugins.append(plugin)

    def available_plugins(self) -> list[str]:
        return [p.info.name for p in self.plugins if p.check_available()]
