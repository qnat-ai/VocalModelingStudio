"""Central logging helpers for Vocal Modeling Studio."""
from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(log_dir: Path, *, session_id: str | None = None) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("vms")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    desired_files = {log_dir / "vms.log"}
    if session_id:
        desired_files.add(log_dir / f"render_{session_id}.log")

    existing_files: set[Path] = set()
    for handler in list(logger.handlers):
        if isinstance(handler, logging.FileHandler):
            existing_files.add(Path(handler.baseFilename))
        elif isinstance(handler, logging.StreamHandler):
            handler.setFormatter(formatter)

    if not any(isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler) for handler in logger.handlers):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    for log_file in desired_files - existing_files:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

