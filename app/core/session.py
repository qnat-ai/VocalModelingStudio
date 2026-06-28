"""Per-run session folder management."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SessionPaths:
    session_id: str
    root_dir: Path
    input_dir: Path
    work_dir: Path
    output_dir: Path
    reports_dir: Path
    metadata_dir: Path

    @classmethod
    def create(cls, projects_dir: Path, *, stamp: str, input_name: str) -> "SessionPaths":
        safe_name = _slugify(input_name)
        session_id = f"{stamp}_{safe_name}"
        root_dir = projects_dir / session_id
        paths = cls(
            session_id=session_id,
            root_dir=root_dir,
            input_dir=root_dir / "input",
            work_dir=root_dir / "work",
            output_dir=root_dir / "output",
            reports_dir=root_dir / "reports",
            metadata_dir=root_dir / "metadata",
        )
        for directory in (paths.root_dir, paths.input_dir, paths.work_dir, paths.output_dir, paths.reports_dir, paths.metadata_dir):
            directory.mkdir(parents=True, exist_ok=True)
        return paths

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {key: str(value) if isinstance(value, Path) else value for key, value in data.items()}

    def write_session_manifest(self, manifest: dict[str, Any]) -> Path:
        path = self.root_dir / "session.yaml"
        path.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return path


def _slugify(value: str) -> str:
    collapsed = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return collapsed or "session"

