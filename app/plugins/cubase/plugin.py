"""Cubase workflow integration placeholder."""
from app.plugins.base import BasePlugin, PluginInfo


class CubasePlugin(BasePlugin):
    info = PluginInfo(name="Cubase", version="manual", notes="Export WAV/MIDI to Cubase project")
