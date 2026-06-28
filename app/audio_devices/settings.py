"""Settings loader for audio device preferences."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AudioDeviceSettings:
    preferred_hostapi_keywords: list[str] = field(default_factory=lambda: ["ASIO"])
    preferred_input_keywords: list[str] = field(default_factory=lambda: ["ASIO4ALL", "ASIO"])
    preferred_output_keywords: list[str] = field(default_factory=lambda: ["ASIO4ALL", "ASIO"])
    fallback_hostapi_keywords: list[str] = field(default_factory=lambda: ["WASAPI", "DirectSound", "MME"])
    default_profile: str = "balanced"
    samplerate: int = 48_000
    channels: int = 1
    dtype: str = "float32"


_DEFAULT_CONFIG_PATH = Path("configs/audio_devices.yaml")


def _as_list(value: Any, default: list[str]) -> list[str]:
    if value is None:
        return default
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def load_audio_device_settings(path: str | Path = _DEFAULT_CONFIG_PATH) -> AudioDeviceSettings:
    """Load audio device settings from YAML.

    Missing files are not fatal; defaults are returned so tests and first run work
    even before configuration is customized.
    """
    config_path = Path(path)
    if not config_path.exists():
        return AudioDeviceSettings()

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    preferred = data.get("preferred", {})
    fallback = data.get("fallback", {})
    runtime = data.get("runtime", {})

    return AudioDeviceSettings(
        preferred_hostapi_keywords=_as_list(preferred.get("hostapi_keywords"), ["ASIO"]),
        preferred_input_keywords=_as_list(preferred.get("input_device_keywords"), ["ASIO4ALL", "ASIO"]),
        preferred_output_keywords=_as_list(preferred.get("output_device_keywords"), ["ASIO4ALL", "ASIO"]),
        fallback_hostapi_keywords=_as_list(fallback.get("hostapi_keywords"), ["WASAPI", "DirectSound", "MME"]),
        default_profile=str(runtime.get("default_profile", "balanced")),
        samplerate=int(runtime.get("samplerate", 48_000)),
        channels=int(runtime.get("channels", 1)),
        dtype=str(runtime.get("dtype", "float32")),
    )
