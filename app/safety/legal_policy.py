"""Legal/safety policy helpers for audio acquisition."""

ALLOWED_LICENSE_HINTS = {"cc0", "cc-by", "public-domain", "own-recording", "licensed"}


def is_license_allowed(license_hint: str) -> bool:
    return license_hint.strip().lower() in ALLOWED_LICENSE_HINTS
