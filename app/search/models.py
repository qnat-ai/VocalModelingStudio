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
    genre: str | None = None
    license_hint: str | None = None

    def as_text(self) -> str:
        parts = [self.artist, self.title, self.genre, self.license_hint, self.isrc]
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
        """Convenience wrapper around the canonical classifier.

        Delegates to ``license_checker.classify_license`` so there is a
        single source of truth for what counts as a safe license. Importing
        here (rather than at module scope) avoids a circular import, since
        ``license_checker`` itself imports ``SearchResult`` from this module.
        """
        from app.search.license_checker import classify_license

        return classify_license(self) == "safe"
