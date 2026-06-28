from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class TrackQuery:
    """User query for searching legal metadata/sources."""

    title: str | None = None
    artist: str | None = None
    isrc: str | None = None

    def as_text(self) -> str:
        parts = [self.artist, self.title, self.isrc]
        return " ".join(part for part in parts if part).strip()


@dataclass(slots=True)
class SearchResult:
    """Normalized search result from metadata/source providers."""

    source: str
    title: str
    artist: str | None = None
    url: str | None = None
    license_name: str | None = None
    license_url: str | None = None
    result_type: str = "metadata"  # metadata, audio, stem, acapella, dataset
    local_path: Path | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def is_probably_legal_for_download(self) -> bool:
        text = f"{self.license_name or ''} {self.license_url or ''}".lower()
        legal_tokens = ["cc0", "cc-by", "creative commons", "public domain", "royalty-free"]
        return any(token in text for token in legal_tokens)
