from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.search.models import SearchResult, TrackQuery

MUSICBRAINZ_API = "https://musicbrainz.org/ws/2/recording/"
USER_AGENT = "VocalModelingStudio/0.2 (local research tool)"


def search_musicbrainz(query: TrackQuery, cache_dir: Path | None = None, limit: int = 5) -> list[SearchResult]:
    """Search MusicBrainz metadata.

    MusicBrainz is used only for identification/metadata. It does not provide
    commercial audio downloads. Internet access is required.
    """
    query_text = query.as_text()
    if not query_text:
        return []

    params = urlencode({"query": query_text, "fmt": "json", "limit": str(limit)})
    url = f"{MUSICBRAINZ_API}?{params}"
    cache_key = "musicbrainz_" + "_".join(query_text.lower().split())[:80] + ".json"
    cache_path = Path(cache_dir / cache_key) if cache_dir else None

    if cache_path and cache_path.exists():
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        request = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    results: list[SearchResult] = []
    for rec in payload.get("recordings", []):
        artist_credit = rec.get("artist-credit") or []
        artist = None
        if artist_credit and isinstance(artist_credit[0], dict):
            artist = artist_credit[0].get("name")
        results.append(
            SearchResult(
                source="musicbrainz",
                title=rec.get("title", "Unknown title"),
                artist=artist,
                url=f"https://musicbrainz.org/recording/{rec.get('id')}",
                license_name="metadata only / CC0 core data",
                result_type="metadata",
                extra={"id": rec.get("id"), "score": rec.get("score")},
            )
        )
    return results
