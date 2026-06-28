"""Helpers for batch processing from CLI."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aiff", ".aif"}


@dataclass(frozen=True)
class BatchItemResult:
    input_path: Path
    success: bool
    output_path: Path | None
    elapsed_sec: float
    error: str = ""


def collect_input_files(
    input_dir: Path,
    *,
    recursive: bool,
    pattern: str | None = None,
    allowed_extensions: set[str] | None = None,
) -> list[Path]:
    if not input_dir.exists() or not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    exts = {ext.lower() for ext in (allowed_extensions or SUPPORTED_AUDIO_EXTENSIONS)}
    glob_pattern = pattern or "*"
    iterator = input_dir.rglob(glob_pattern) if recursive else input_dir.glob(glob_pattern)

    files = [path for path in iterator if path.is_file() and path.suffix.lower() in exts]
    return sorted(files, key=lambda p: p.as_posix().lower())


def run_batch(
    pipeline: Any,
    input_files: list[Path],
    *,
    reference_path: Path | None = None,
    export_for_audacity: bool = False,
    continue_on_error: bool = False,
) -> list[BatchItemResult]:
    results: list[BatchItemResult] = []
    for input_path in input_files:
        start = perf_counter()
        try:
            output_path = pipeline.run(
                input_path=input_path,
                reference_path=reference_path,
                export_for_audacity=export_for_audacity,
                output_path=None,
            )
            results.append(
                BatchItemResult(
                    input_path=input_path,
                    success=True,
                    output_path=Path(output_path),
                    elapsed_sec=perf_counter() - start,
                )
            )
        except Exception as exc:
            results.append(
                BatchItemResult(
                    input_path=input_path,
                    success=False,
                    output_path=None,
                    elapsed_sec=perf_counter() - start,
                    error=str(exc),
                )
            )
            if not continue_on_error:
                raise
    return results

