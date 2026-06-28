from app.search.models import TrackQuery
from app.search.source_catalog import suggest_legal_sources


def test_source_catalog_returns_results():
    results = suggest_legal_sources(TrackQuery(title="Test", artist="Artist"))
    assert results
    assert any("MUSDB" in result.source for result in results)
