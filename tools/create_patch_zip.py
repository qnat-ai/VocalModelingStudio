"""Create a clean ZIP archive of the project for sharing/patching.

Excludes caches, logs, and locally generated run data (see EXCLUDE_PATTERNS)
so the archive only contains source files meant to be shared or committed.

Usage:
    python tools/create_patch_zip.py
    python tools/create_patch_zip.py --output dist/VocalModelingStudio_patch.zip
    python tools/create_patch_zip.py --base-dir . --output my_patch.zip
"""
from __future__ import annotations

import argparse
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
    ".git",
    ".idea",
    ".venv",
    "venv",
)


def create_zip(output: Path, files: list[Path], base_dir: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
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
        if relative_path == pattern or relative_path.startswith(pattern + "/") or f"/{pattern}/" in f"/{relative_path}":
            # Keep explicitly whitelisted placeholder files.
            if relative_path.endswith("/.gitkeep"):
                return False
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a clean patch ZIP of the project.")
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Project root to package (default: repository root).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output ZIP path (default: <base-dir>/dist/<project-name>_patch.zip).",
    )
    args = parser.parse_args()

    base_dir = args.base_dir.resolve()
    output = args.output or (base_dir / "dist" / f"{base_dir.name}_patch.zip")

    files = collect_patch_files(base_dir)
    create_zip(output, files, base_dir)
    print(f"Wrote {len(files)} files to {output}")


if __name__ == "__main__":
    main()

