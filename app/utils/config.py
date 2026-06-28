from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Nie znaleziono pliku konfiguracji: {path}")
    with path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    if not isinstance(config, dict):
        raise ValueError("Konfiguracja musi być mapą YAML (dict).")

    expected_sections = {
        "audio",
        "processing",
        "paths",
        "mastering",
        "integration",
        "quality_guardrails",
    }
    unknown_sections = set(config) - expected_sections
    if unknown_sections:
        raise ValueError(f"Nieznane sekcje konfiguracji: {sorted(unknown_sections)}")

    audio_cfg = config.get("audio", {})
    if audio_cfg and not isinstance(audio_cfg, dict):
        raise ValueError("Sekcja 'audio' musi być mapą.")
    if "sample_rate" in audio_cfg and int(audio_cfg["sample_rate"]) <= 0:
        raise ValueError("audio.sample_rate musi być > 0")
