from __future__ import annotations

import json
from types import SimpleNamespace

from app.search.downloader import search_archive_org, search_freesound


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_search_freesound_maps_results(monkeypatch):
    payload = {
        "results": [
            {
                "id": 11,
                "name": "Vocal one-shot",
                "username": "tester",
                "license": "Creative Commons 0",
                "previews": {"preview-hq-mp3": "https://cdn.example/vocal.mp3"},
            }
        ]
    }

    monkeypatch.setattr("app.search.downloader.urlopen", lambda request, timeout: _FakeResponse(payload))

    results = search_freesound("vocal", "token", limit=1)

    assert len(results) == 1
    assert results[0].source == "Freesound"
    assert results[0].url == "https://cdn.example/vocal.mp3"


def test_search_archive_org_maps_results(monkeypatch):
    payload = {
        "response": {
            "docs": [
                {
                    "identifier": "demo-item",
                    "title": "Demo Item",
                    "creator": "Archive User",
                    "licenseurl": "https://creativecommons.org/publicdomain/zero/1.0/",
                }
            ]
        }
    }

    monkeypatch.setattr("app.search.downloader.urlopen", lambda request, timeout: _FakeResponse(payload))

    results = search_archive_org("demo", limit=1)

    assert len(results) == 1
    assert results[0].source == "Archive.org"
    assert "demo-item" in (results[0].url or "")
    # license_name is intentionally left unset; classification should be
    # driven by inspecting license_url content, not guessed at mapping time.
    assert results[0].license_name is None
    assert results[0].license_url == "https://creativecommons.org/publicdomain/zero/1.0/"


def test_search_archive_org_does_not_assume_public_domain_for_any_licenseurl(monkeypatch):
    """Regression test: a non-commercial CC licenseurl must not be mislabeled.

    Previously, any present ``licenseurl`` was mapped straight to
    ``license_name="public domain"``, which is wrong for restrictive
    licenses such as CC BY-NC. The mapping must stay license-url-driven.
    """
    payload = {
        "response": {
            "docs": [
                {
                    "identifier": "nc-item",
                    "title": "Non-commercial Item",
                    "creator": "Archive User",
                    "licenseurl": "https://creativecommons.org/licenses/by-nc/4.0/",
                }
            ]
        }
    }

    monkeypatch.setattr("app.search.downloader.urlopen", lambda request, timeout: _FakeResponse(payload))

    results = search_archive_org("demo", limit=1)

    assert len(results) == 1
    assert results[0].license_name is None
    assert results[0].is_probably_legal_for_download is False

