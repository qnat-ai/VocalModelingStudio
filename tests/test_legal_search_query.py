from __future__ import annotations

from app.gui.gradio.legal_search_panel import build_track_query


def test_track_query_accepts_genre_and_license_hint() -> None:
    query = build_track_query(
        title="Song",
        artist="Artist",
        isrc=None,
        genre="soul",
        license_hint="CC0",
    )
    text = query.as_text()
    assert "Artist" in text
    assert "Song" in text
    assert "soul" in text
    assert "CC0" in text
