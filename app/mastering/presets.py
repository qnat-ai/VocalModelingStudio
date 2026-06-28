"""Reusable mastering preset definitions."""
from __future__ import annotations

from typing import Any


def neutral_mastering_preset(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "enable_highpass": True,
        "highpass_hz": 80.0,
        "compressor_threshold_db": -12.0,
        "compressor_ratio": 1.3,
        "limiter_ceiling_db": -6.0,
        "makeup_gain_db": 0.0,
        "adaptive_enabled": False,
        "air_amount": 0.0,
        "stereo_width": 1.0,
    }
    if overrides:
        data.update(overrides)
    return data

