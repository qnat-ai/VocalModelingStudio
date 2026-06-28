"""External FX bridge for CLI-driven VST/RX processing."""
from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExternalFxSettings:
    enabled: bool = False
    command_template: tuple[str, ...] = ()
    preset: str = ""
    strict: bool = False
    command_preset: str = ""
    preset_library: dict[str, tuple[str, ...]] | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any] | None = None) -> "ExternalFxSettings":
        data = data or {}
        preset_library: dict[str, tuple[str, ...]] = {}
        for name, raw_value in (data.get("preset_library", {}) or {}).items():
            if isinstance(raw_value, str):
                preset_library[str(name)] = tuple(shlex.split(raw_value, posix=False))
            elif isinstance(raw_value, list):
                preset_library[str(name)] = tuple(str(item) for item in raw_value)

        raw_template = data.get("command_template", [])
        if isinstance(raw_template, str):
            template = tuple(shlex.split(raw_template, posix=False))
        elif isinstance(raw_template, list):
            template = tuple(str(item) for item in raw_template)
        else:
            template = ()
        command_preset = str(data.get("command_preset", ""))
        if not template and command_preset and command_preset in preset_library:
            template = preset_library[command_preset]
        return cls(
            enabled=bool(data.get("enabled", False)),
            command_template=template,
            preset=str(data.get("preset", "")),
            strict=bool(data.get("strict", False)),
            command_preset=command_preset,
            preset_library=preset_library or None,
        )


class ExternalFxBridge:
    def __init__(self, settings: ExternalFxSettings) -> None:
        self.settings = settings

    @classmethod
    def from_config(cls, config: dict[str, Any] | None = None) -> "ExternalFxBridge":
        return cls(ExternalFxSettings.from_mapping(config))

    def process_file(self, input_path: Path, output_path: Path, *, preset: str | None = None) -> Path:
        if not self.settings.enabled:
            return input_path
        if not self.settings.command_template:
            raise ValueError("External FX is enabled, but command_template is empty.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        used_preset = preset if preset is not None else self.settings.preset
        command = [
            token.format(input=str(input_path), output=str(output_path), preset=used_preset)
            for token in self.settings.command_template
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            details = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(f"External FX command failed: {details}")
        if not output_path.exists():
            raise RuntimeError("External FX command did not produce output file.")
        return output_path


