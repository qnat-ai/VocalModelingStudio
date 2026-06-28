"""Plugin base interfaces."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PluginInfo:
    name: str
    version: str
    enabled: bool = False
    notes: str = ""


class BasePlugin:
    info = PluginInfo(name="base", version="0.0")

    def check_available(self) -> bool:
        return False
