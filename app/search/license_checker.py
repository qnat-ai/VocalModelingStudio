from __future__ import annotations

from app.search.models import SearchResult

SAFE_LICENSE_KEYWORDS = (
    "cc0",
    "cc-by",
    "creative commons attribution",
    "public domain",
    "royalty-free",
)

RESTRICTED_KEYWORDS = (
    "all rights reserved",
    "unknown",
    "copyright",
    "non-commercial",
    "nc",
)


def classify_license(result: SearchResult) -> str:
    """Return: safe, restricted, unknown.

    This is intentionally conservative. When unsure, the program should not
    auto-download. It should only present metadata and ask the user to verify.
    """
    text = f"{result.license_name or ''} {result.license_url or ''}".lower()
    if any(keyword in text for keyword in SAFE_LICENSE_KEYWORDS):
        return "safe"
    if any(keyword in text for keyword in RESTRICTED_KEYWORDS):
        return "restricted"
    return "unknown"


def require_safe_license(result: SearchResult) -> None:
    status = classify_license(result)
    if status != "safe":
        raise PermissionError(
            f"Source '{result.source}' / '{result.title}' has license status '{status}'. "
            "Auto-download disabled. Verify rights manually."
        )
