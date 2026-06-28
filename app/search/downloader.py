from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from app.search.license_checker import require_safe_license
from app.search.models import SearchResult


def download_if_legal(result: SearchResult, output_dir: Path) -> Path:
    """Download a result only if the license was classified as safe.

    This function is intentionally minimal and conservative. Many services need
    their official API, authentication, or explicit manual download flow.
    """
    require_safe_license(result)
    if not result.url:
        raise ValueError("Result has no URL to download.")

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = result.title.replace("/", "_").replace("\\", "_") + ".download"
    output_path = output_dir / filename
    request = Request(result.url, headers={"User-Agent": "VocalModelingStudio/0.2"})
    with urlopen(request, timeout=30) as response:
        output_path.write_bytes(response.read())
    return output_path


def search_freesound(query: str, api_key: str, *, limit: int = 10) -> list[SearchResult]:
    if not query.strip():
        return []
    if not api_key.strip():
        raise ValueError("Freesound API key is required.")

    encoded = quote_plus(query)
    url = (
        "https://freesound.org/apiv2/search/text/"
        f"?query={encoded}&page_size={int(limit)}"
        "&fields=id,name,username,license,previews"
    )
    request = Request(url, headers={"Authorization": f"Token {api_key}", "User-Agent": "VocalModelingStudio/0.2"})
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    results: list[SearchResult] = []
    for item in payload.get("results", []):
        previews = item.get("previews") or {}
        preview_url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")
        results.append(
            SearchResult(
                source="Freesound",
                title=str(item.get("name", "untitled")),
                artist=item.get("username"),
                url=preview_url,
                license_name=item.get("license"),
                result_type="audio",
                extra={"id": item.get("id")},
            )
        )
    return results


def search_archive_org(query: str, *, limit: int = 10) -> list[SearchResult]:
    if not query.strip():
        return []

    encoded = quote_plus(query)
    url = (
        "https://archive.org/advancedsearch.php"
        f"?q={encoded}&fl[]=identifier&fl[]=title&fl[]=creator&fl[]=licenseurl"
        "&output=json"
        f"&rows={int(limit)}"
    )
    request = Request(url, headers={"User-Agent": "VocalModelingStudio/0.2"})
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    docs = payload.get("response", {}).get("docs", [])
    results: list[SearchResult] = []
    for item in docs:
        identifier = item.get("identifier")
        if not identifier:
            continue
        item_url = f"https://archive.org/details/{identifier}"
        results.append(
            SearchResult(
                source="Archive.org",
                title=str(item.get("title", identifier)),
                artist=item.get("creator"),
                url=item_url,
                license_name="public domain" if item.get("licenseurl") else None,
                license_url=item.get("licenseurl"),
                result_type="dataset",
                extra={"identifier": identifier},
            )
        )
    return results

