from __future__ import annotations

from pathlib import Path

from app.search.local_library import search_local_library
from app.search.metadata_search import search_musicbrainz
from app.search.models import SearchResult, TrackQuery
from app.search.source_catalog import suggest_legal_sources


class SearchManager:
    def __init__(self, legal_sources_dir: Path, cache_dir: Path) -> None:
        self.legal_sources_dir = Path(legal_sources_dir)
        self.cache_dir = Path(cache_dir)

    def search(self, query: TrackQuery, online_metadata: bool = False) -> list[SearchResult]:
        results: list[SearchResult] = []
        results.extend(search_local_library(query, self.legal_sources_dir))
        if online_metadata:
            try:
                results.extend(search_musicbrainz(query, cache_dir=self.cache_dir))
            except Exception as exc:  # network should not break local workflow
                results.append(
                    SearchResult(
                        source="musicbrainz",
                        title="Metadata search failed",
                        result_type="error",
                        extra={"error": str(exc)},
                    )
                )
        results.extend(suggest_legal_sources(query))
        return results
