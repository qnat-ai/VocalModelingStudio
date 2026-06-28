"""Utility placeholder for future patch ZIP generation."""
from __future__ import annotations

from pathlib import Path
import zipfile

EXCLUDE_PATTERNS = (
    "__pycache__",
    ".pytest_cache",
    "*.pyc",
    "data/work",
    "data/output",
    "data/projects",
    "logs",
)


def create_zip(output: Path, files: list[Path], base_dir: Path) -> None:
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            zf.write(file, file.relative_to(base_dir))


def collect_patch_files(base_dir: Path) -> list[Path]:
    selected: list[Path] = []
    for path in base_dir.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(base_dir).as_posix()
        if _is_excluded(rel):
            continue
        if rel.endswith("/.gitkeep"):
            selected.append(path)
            continue
        selected.append(path)
    return selected


def _is_excluded(relative_path: str) -> bool:
    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith("*"):
            if relative_path.endswith(pattern[1:]):
                return True
            continue
        if relative_path == pattern or relative_path.startswith(pattern + "/"):
            # Keep explicitly whitelisted placeholder files.
            if relative_path.endswith("/.gitkeep"):
                return False
            return True
    return False

