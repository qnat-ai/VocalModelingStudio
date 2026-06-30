from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class DependencyStatus:
    name: str
    required: bool
    available: bool
    hint: str = ""


def check_dependencies(extra_bins: Iterable[str] | None = None) -> list[DependencyStatus]:
    bins = [
        ("ffmpeg", True, "Wymagane dla presetow FFmpeg w External FX."),
        ("demucs", False, "Opcjonalne: separacja wokalu/stemow."),
        ("rvc", False, "Opcjonalne: backend rvc_cli."),
        ("rx_cli", False, "Opcjonalne: zewnetrzny chain RX CLI."),
    ]
    if extra_bins:
        for binary in extra_bins:
            bins.append((str(binary), False, "Dodatkowe narzedzie zewnetrzne."))

    statuses: list[DependencyStatus] = []
    for name, required, hint in bins:
        statuses.append(
            DependencyStatus(
                name=name,
                required=required,
                available=shutil.which(name) is not None,
                hint=hint,
            )
        )
    return statuses


def format_dependency_report(statuses: list[DependencyStatus]) -> str:
    lines = ["VocalModelingStudio dependency check", ""]
    for item in statuses:
        level = "REQ" if item.required else "OPT"
        state = "OK" if item.available else "MISSING"
        lines.append(f"[{level}] {item.name}: {state}")
        if item.hint:
            lines.append(f"      {item.hint}")
    return "\n".join(lines) + "\n"

