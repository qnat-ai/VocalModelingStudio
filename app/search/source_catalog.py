from __future__ import annotations

from app.search.models import SearchResult, TrackQuery

LEGAL_SOURCE_CATALOG = [
    {
        "name": "MUSDB18 / MUSDB18-HQ",
        "url": "https://sigsep.github.io/datasets/musdb.html",
        "type": "dataset/stems",
        "note": "Research dataset with vocals, drums, bass, other. Check access/license terms.",
    },
    {
        "name": "MedleyDB",
        "url": "https://medleydb.weebly.com/",
        "type": "dataset/multitrack",
        "note": "Royalty-free multitrack dataset useful for melody and stem experiments.",
    },
    {
        "name": "ccMixter",
        "url": "https://ccmixter.org/",
        "type": "creative-commons/acapella/remix",
        "note": "Community remixes and a cappellas under Creative Commons; verify each track license.",
    },
    {
        "name": "Freesound",
        "url": "https://freesound.org/",
        "type": "creative-commons/samples",
        "note": "Short vocal samples and field recordings; API available; verify each sample license.",
    },
    {
        "name": "Internet Archive",
        "url": "https://archive.org/",
        "type": "archive/audio",
        "note": "Large public archive. License quality varies; verify before download/use.",
    },
    {
        "name": "Jamendo",
        "url": "https://www.jamendo.com/",
        "type": "independent/cc-music",
        "note": "Useful for legal music discovery; stems are not guaranteed.",
    },
]


def suggest_legal_sources(query: TrackQuery) -> list[SearchResult]:
    """Return catalog suggestions. No scraping, no unsafe downloading."""
    title = query.title or "Legal vocal/stem search"
    return [
        SearchResult(
            source=item["name"],
            title=title,
            artist=query.artist,
            url=item["url"],
            license_name="varies / verify manually",
            result_type=item["type"],
            extra={"note": item["note"]},
        )
        for item in LEGAL_SOURCE_CATALOG
    ]
