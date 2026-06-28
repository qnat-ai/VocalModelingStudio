from __future__ import annotations

import pytest

from app.utils.config import validate_config


def test_validate_config_accepts_known_sections():
    validate_config(
        {
            "audio": {"sample_rate": 48000},
            "processing": {},
            "paths": {},
            "mastering": {},
            "integration": {},
            "quality_guardrails": {},
        }
    )


def test_validate_config_rejects_unknown_sections():
    with pytest.raises(ValueError):
        validate_config({"audio": {}, "unknown_section": {}})

