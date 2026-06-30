from __future__ import annotations

from pathlib import Path
from typing import Any

from app.search.downloader import download_if_legal, search_archive_org, search_freesound
from app.search.license_checker import classify_license
from app.search.models import SearchResult, TrackQuery
from app.search.search_manager import SearchManager

RESULT_HEADERS = [
    "#",
    "Status",
    "Źródło",
    "Typ",
    "Wykonawca",
    "Tytuł",
    "Licencja",
    "URL / lokalizacja",
    "Notatka",
]


def build_track_query(
    title: str | None,
    artist: str | None,
    isrc: str | None,
    genre: str | None = None,
    license_hint: str | None = None,
) -> TrackQuery:
    """Create a normalized search query from GUI text fields."""

    return TrackQuery(
        title=(title or "").strip() or None,
        artist=(artist or "").strip() or None,
        isrc=(isrc or "").strip() or None,
        genre=(genre or "").strip() or None,
        license_hint=(license_hint or "").strip() or None,
    )


def result_to_dict(result: SearchResult) -> dict[str, Any]:
    """Serialize SearchResult for Gradio state."""

    return {
        "source": result.source,
        "title": result.title,
        "artist": result.artist,
        "url": result.url,
        "license_name": result.license_name,
        "license_url": result.license_url,
        "result_type": result.result_type,
        "local_path": str(result.local_path) if result.local_path else None,
        "extra": dict(result.extra or {}),
        "status": classify_license(result),
    }


def result_from_dict(payload: dict[str, Any]) -> SearchResult:
    """Rebuild SearchResult from Gradio state."""

    local_path = payload.get("local_path")
    return SearchResult(
        source=str(payload.get("source") or "unknown"),
        title=str(payload.get("title") or "untitled"),
        artist=payload.get("artist"),
        url=payload.get("url"),
        license_name=payload.get("license_name"),
        license_url=payload.get("license_url"),
        result_type=str(payload.get("result_type") or "metadata"),
        local_path=Path(local_path) if local_path else None,
        extra=dict(payload.get("extra") or {}),
    )


def results_to_table(results: list[dict[str, Any]]) -> list[list[str]]:
    """Format serialized results as rows for gr.Dataframe."""

    rows: list[list[str]] = []
    for index, item in enumerate(results, start=1):
        location = item.get("local_path") or item.get("url") or "-"
        rows.append(
            [
                str(index),
                str(item.get("status") or "unknown"),
                str(item.get("source") or "-"),
                str(item.get("result_type") or "-"),
                str(item.get("artist") or "-"),
                str(item.get("title") or "-"),
                str(item.get("license_name") or item.get("license_url") or "-"),
                str(location),
                str((item.get("extra") or {}).get("note") or (item.get("extra") or {}).get("error") or ""),
            ]
        )
    return rows


def search_legal_sources_for_gui(
    title: str | None,
    artist: str | None,
    isrc: str | None,
    genre: str | None,
    license_hint: str | None,
    use_local_catalog: bool,
    use_musicbrainz: bool,
    use_freesound: bool,
    freesound_api_key: str | None,
    use_archive: bool,
    safe_only: bool,
    limit: int | float | None,
    legal_sources_dir: str | Path = "data/legal_sources",
    cache_dir: str | Path = "data/search_cache",
) -> tuple[list[list[str]], list[dict[str, Any]], str]:
    """Search legal sources and return table rows + serialized state.

    Legal Search is a discovery helper: title, artist, genre, license and
    metadata can be used to find legal audio sources. Downloads remain limited
    to results classified as safe by app.search.license_checker.
    """

    query = build_track_query(
        title=title,
        artist=artist,
        isrc=isrc,
        genre=genre,
        license_hint=license_hint,
    )
    query_text = query.as_text()
    if not query_text:
        return [], [], "Podaj tytuł, wykonawcę, gatunek, licencję albo ISRC."

    safe_limit = max(1, min(int(limit or 10), 50))
    results: list[SearchResult] = []
    warnings: list[str] = []

    if use_local_catalog or use_musicbrainz:
        manager = SearchManager(
            legal_sources_dir=Path(legal_sources_dir),
            cache_dir=Path(cache_dir),
        )
        try:
            results.extend(manager.search(query, online_metadata=bool(use_musicbrainz)))
        except Exception as exc:  # keep GUI usable even if a provider fails
            warnings.append(f"Local/MusicBrainz search failed: {exc}")

    if use_freesound:
        if not (freesound_api_key or "").strip():
            warnings.append("Freesound pominięty: wymagany jest API key.")
        else:
            try:
                results.extend(search_freesound(query_text, str(freesound_api_key), limit=safe_limit))
            except Exception as exc:
                warnings.append(f"Freesound API błąd: {exc}")

    if use_archive:
        try:
            results.extend(search_archive_org(query_text, limit=safe_limit))
        except Exception as exc:
            warnings.append(f"Archive.org API błąd: {exc}")

    serialized = [result_to_dict(result) for result in results]
    if safe_only:
        serialized = [item for item in serialized if item.get("status") == "safe"]

    table = results_to_table(serialized)
    summary_parts = [
        f"Zapytanie: `{query_text}`",
        f"Wyniki: **{len(serialized)}**",
    ]
    if safe_only:
        summary_parts.append("Filtr: tylko `safe`.")
    else:
        summary_parts.append("Filtr: pokazuję także `unknown/restricted` do ręcznej weryfikacji.")
    if warnings:
        summary_parts.append("\n".join(f"⚠️ {warning}" for warning in warnings))

    return table, serialized, "\n\n".join(summary_parts)


def download_selected_safe_result_for_gui(
    serialized_results: list[dict[str, Any]] | None,
    selected_number: int | float | None,
    download_dir: str | Path = "data/search_cache/downloads",
) -> str:
    """Download selected safe result by 1-based GUI number."""

    if not serialized_results:
        return "Brak wyników do pobrania. Najpierw wykonaj wyszukiwanie."

    try:
        index = int(selected_number or 0) - 1
    except (TypeError, ValueError):
        return "Podaj poprawny numer wyniku z tabeli."

    if index < 0 or index >= len(serialized_results):
        return f"Numer poza zakresem. Dostępne wyniki: 1-{len(serialized_results)}."

    result = result_from_dict(serialized_results[index])
    status = classify_license(result)
    if status != "safe":
        return f"Nie pobieram: status licencji to `{status}`. Pobieranie automatyczne jest tylko dla `safe`."

    if not result.url:
        return "Wybrany wynik nie ma URL do pobrania."

    try:
        path = download_if_legal(result, Path(download_dir))
    except Exception as exc:
        return f"Pobieranie nie powiodło się: {exc}"

    return f"Pobrano: {path}"
