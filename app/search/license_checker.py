from __future__ import annotations

import re

from app.search.models import SearchResult

SAFE_LICENSE_KEYWORDS = (
    "cc0",
    "cc-by",
    "creative commons attribution",
    "public domain",
    "royalty-free",
)

# Plain substrings are fine here: each one is long/specific enough that it
# will not accidentally match unrelated text (unlike a bare "nc").
RESTRICTED_SUBSTRINGS = (
    "all rights reserved",
    "unknown",
    "copyright",
    "non-commercial",
    "noncommercial",
)

# "nc" (the CC "NonCommercial" abbreviation, e.g. "CC BY-NC") is too short to
# match as a plain substring -- it would also match unrelated text containing
# those two letters (names, other words, etc.). Match it only as a standalone
# token instead.
_RESTRICTED_WORD_PATTERN = re.compile(r"\bnc\b")


def classify_license(result: SearchResult) -> str:
    """Return: safe, restricted, unknown.

    This is intentionally conservative. When unsure, the program should not
    auto-download. It should only present metadata and ask the user to verify.
    """
    text = f"{result.license_name or ''} {result.license_url or ''}".lower()
    if any(keyword in text for keyword in SAFE_LICENSE_KEYWORDS):
        return "safe"
    if any(keyword in text for keyword in RESTRICTED_SUBSTRINGS):
        return "restricted"
    if _RESTRICTED_WORD_PATTERN.search(text):
        return "restricted"
    return "unknown"


def require_safe_license(result: SearchResult) -> None:
    status = classify_license(result)
    if status != "safe":
        raise PermissionError(
            f"Source '{result.source}' / '{result.title}' has license status '{status}'. "
            "Auto-download disabled. Verify rights manually."
        )
