"""Realtime configuration loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.audio_devices.latency_profiles import LatencyProfile, get_latency_profile


@dataclass(frozen=True)
class RealtimeConfig:
    profile_name: str
    samplerate: int
    blocksize: int
    latency: str | float
    channels: int
    allow_heavy_ai_in_callback: bool = False
    overflow_warning: bool = True

    @classmethod
    def from_profile(cls, profile: LatencyProfile, *, allow_heavy_ai_in_callback: bool = False) -> "RealtimeConfig":
        return cls(
            profile_name=profile.name,
            samplerate=profile.samplerate,
            blocksize=profile.blocksize,
            latency=profile.latency,
            channels=profile.channels,
            allow_heavy_ai_in_callback=allow_heavy_ai_in_callback,
        )


_DEFAULT_REALTIME_CONFIG = Path("configs/realtime.yaml")


def load_realtime_config(
    path: str | Path = _DEFAULT_REALTIME_CONFIG,
    profile_name: str | None = None,
) -> RealtimeConfig:
    """Load realtime configuration from YAML or predefined profile."""
    config_path = Path(path)
    if not config_path.exists():
        return RealtimeConfig.from_profile(get_latency_profile(profile_name or "balanced"))

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    engine = data.get("engine", {})
    selected = profile_name or str(engine.get("default_profile", "balanced"))
    profiles: dict[str, Any] = data.get("profiles", {})

    if selected not in profiles:
        return RealtimeConfig.from_profile(get_latency_profile(selected))

    raw = profiles[selected]
    return RealtimeConfig(
        profile_name=selected,
        samplerate=int(raw.get("samplerate", 48_000)),
        blocksize=int(raw.get("blocksize", 512)),
        latency=raw.get("latency", "low"),
        channels=int(raw.get("channels", 1)),
        allow_heavy_ai_in_callback=bool(engine.get("allow_heavy_ai_in_callback", False)),
        overflow_warning=bool(engine.get("overflow_warning", True)),
    )
