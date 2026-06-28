from __future__ import annotations

from pathlib import Path

from app.search.models import SearchResult, TrackQuery

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aiff"}


def search_local_library(query: TrackQuery, root: Path) -> list[SearchResult]:
    """Search local legal library by filename/path.

    Put owned audio, remix packs, a cappellas or dataset stems under
    data/legal_sources/. The search is simple by design and works offline.
    """
    root = Path(root)
    if not root.exists():
        return []

    terms = [term.lower() for term in [query.artist, query.title, query.isrc] if term]
    results: list[SearchResult] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        searchable = str(path.relative_to(root)).lower()
        if terms and not all(term in searchable for term in terms):
            continue
        result_type = "audio"
        lowered_name = path.name.lower()
        if "acapella" in lowered_name or "a cappella" in lowered_name or "vocal" in lowered_name:
            result_type = "acapella"
        if "stem" in searchable or "vocals" in lowered_name:
            result_type = "stem"
        results.append(
            SearchResult(
                source="local_library",
                title=path.stem,
                artist=query.artist,
                local_path=path,
                license_name="user-provided / verify manually",
                result_type=result_type,
            )
        )
    return results
