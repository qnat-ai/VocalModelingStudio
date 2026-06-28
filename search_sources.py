from __future__ import annotations

import argparse
from pathlib import Path

from app.search.downloader import download_if_legal, search_archive_org, search_freesound
from app.search.license_checker import classify_license
from app.search.models import TrackQuery
from app.search.search_manager import SearchManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Legal audio/stem source search")
    parser.add_argument("--title", default=None, help="Tytuł utworu")
    parser.add_argument("--artist", default=None, help="Wykonawca")
    parser.add_argument("--isrc", default=None, help="Opcjonalny kod ISRC")
    parser.add_argument("--online-metadata", action="store_true", help="Włącz wyszukiwanie metadanych MusicBrainz")
    parser.add_argument("--freesound", action="store_true", help="Dodaj wyszukiwanie API Freesound")
    parser.add_argument("--freesound-api-key", default="", help="Token API Freesound")
    parser.add_argument("--archive", action="store_true", help="Dodaj wyszukiwanie API Archive.org")
    parser.add_argument("--limit", type=int, default=10, help="Maksymalna liczba wyników na źródło API")
    parser.add_argument("--download-legal", action="store_true", help="Pobierz automatycznie tylko wyniki z bezpieczną licencją")
    parser.add_argument("--download-dir", default="data/search_cache/downloads", help="Folder docelowy pobrań")
    parser.add_argument("--legal-dir", default="data/legal_sources")
    parser.add_argument("--cache-dir", default="data/search_cache")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manager = SearchManager(
        legal_sources_dir=Path(args.legal_dir),
        cache_dir=Path(args.cache_dir),
    )
    query = TrackQuery(title=args.title, artist=args.artist, isrc=args.isrc)
    results = manager.search(query, online_metadata=args.online_metadata)

    query_text = query.as_text()
    if args.freesound:
        if not args.freesound_api_key.strip():
            print("UWAGA: --freesound wymaga --freesound-api-key. Pomijam Freesound.")
        else:
            try:
                results.extend(search_freesound(query_text, args.freesound_api_key, limit=args.limit))
            except Exception as exc:
                print(f"UWAGA: Freesound API błąd: {exc}")

    if args.archive:
        try:
            results.extend(search_archive_org(query_text, limit=args.limit))
        except Exception as exc:
            print(f"UWAGA: Archive.org API błąd: {exc}")

    print("\nLEGAL SEARCH RESULTS")
    print("=" * 80)
    for index, result in enumerate(results, start=1):
        status = classify_license(result)
        location = result.local_path or result.url or "-"
        print(f"{index}. [{result.source}] {result.artist or '-'} - {result.title}")
        print(f"   type: {result.result_type} | license: {result.license_name or '-'} | status: {status}")
        print(f"   location: {location}")
        if result.extra.get("note"):
            print(f"   note: {result.extra['note']}")
        if result.extra.get("error"):
            print(f"   error: {result.extra['error']}")
        print()

    if args.download_legal:
        download_dir = Path(args.download_dir)
        downloaded = 0
        for result in results:
            if classify_license(result) != "safe":
                continue
            if not result.url:
                continue
            try:
                path = download_if_legal(result, download_dir)
                downloaded += 1
                print(f"POBRANO: {path}")
            except Exception as exc:
                print(f"POMINIETO: [{result.source}] {result.title} -> {exc}")
        print(f"Pobrane pliki: {downloaded}")


if __name__ == "__main__":
    main()
