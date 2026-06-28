"""Audacity integration notes.

Audacity can be used through exported WAV files and optional macro text files.
"""
from app.plugins.base import BasePlugin, PluginInfo


class AudacityPlugin(BasePlugin):
    info = PluginInfo(name="Audacity", version="manual-macro", notes="WAV export + macros")
