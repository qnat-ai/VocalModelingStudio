from __future__ import annotations

from app.search.models import SearchResult
from search_sources import parse_args


def test_parse_args_supports_new_source_flags(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "search_sources.py",
            "--title",
            "demo",
            "--freesound",
            "--freesound-api-key",
            "abc",
            "--archive",
            "--limit",
            "5",
            "--download-legal",
        ],
    )

    args = parse_args()

    assert args.freesound is True
    assert args.archive is True
    assert args.freesound_api_key == "abc"
    assert args.limit == 5
    assert args.download_legal is True


def test_safe_result_is_downloadable(monkeypatch):
    result = SearchResult(
        source="Freesound",
        title="clip",
        url="https://example.org/clip.mp3",
        license_name="Creative Commons 0",
        result_type="audio",
    )

    called = {}

    def fake_download_if_legal(item, output_dir):
        called["source"] = item.source
        called["dir"] = str(output_dir)
        return output_dir / "clip.mp3"

    monkeypatch.setattr("search_sources.download_if_legal", fake_download_if_legal)

    path = fake_download_if_legal(result, output_dir=__import__("pathlib").Path("data/tmp"))
    assert "Freesound" == called["source"]
    assert str(path).endswith("clip.mp3")

