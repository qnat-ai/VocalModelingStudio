"""Latency profiles used by the realtime audio layer.

The values here are deliberately conservative. They are intended for preview and
monitoring, not for running heavy AI models inside an audio callback.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LatencyProfile:
    name: str
    samplerate: int
    blocksize: int
    latency: str | float
    channels: int
    description: str


_PROFILES: dict[str, LatencyProfile] = {
    "safe": LatencyProfile(
        name="safe",
        samplerate=48_000,
        blocksize=1024,
        latency="high",
        channels=1,
        description="Stable test profile for weaker machines.",
    ),
    "balanced": LatencyProfile(
        name="balanced",
        samplerate=48_000,
        blocksize=512,
        latency="low",
        channels=1,
        description="Default starting profile for laptop monitoring.",
    ),
    "low": LatencyProfile(
        name="low",
        samplerate=48_000,
        blocksize=256,
        latency="low",
        channels=1,
        description="Lower latency; may crackle on weaker machines.",
    ),
    "realtime_experimental": LatencyProfile(
        name="realtime_experimental",
        samplerate=48_000,
        blocksize=128,
        latency="low",
        channels=1,
        description="Experimental preview profile; avoid heavy processing.",
    ),
}


def list_latency_profiles() -> list[LatencyProfile]:
    """Return all predefined latency profiles."""
    return list(_PROFILES.values())


def get_latency_profile(name: str = "balanced") -> LatencyProfile:
    """Return a latency profile by name.

    Raises:
        KeyError: if the profile does not exist.
    """
    normalized = name.strip().lower()
    if normalized not in _PROFILES:
        available = ", ".join(sorted(_PROFILES))
        raise KeyError(f"Unknown latency profile '{name}'. Available: {available}")
    return _PROFILES[normalized]
