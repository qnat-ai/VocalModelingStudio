"""Realtime diagnostics helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.audio_devices.device_manager import AudioDeviceManager, SoundDeviceUnavailableError
from app.realtime.config import RealtimeConfig


def build_audio_diagnostics_report(config: RealtimeConfig) -> list[str]:
    """Build a human-readable diagnostics report."""
    lines: list[str] = []
    lines.append("VocalModelingStudio — realtime audio diagnostics")
    lines.append(f"profile: {config.profile_name}")
    lines.append(f"samplerate: {config.samplerate}")
    lines.append(f"blocksize: {config.blocksize}")
    lines.append(f"latency: {config.latency}")
    lines.append(f"channels: {config.channels}")
    lines.append(f"heavy AI in callback: {config.allow_heavy_ai_in_callback}")

    try:
        manager = AudioDeviceManager()
        hostapis = manager.query_hostapis()
        lines.append("")
        lines.append("Host APIs:")
        for api in hostapis:
            lines.append(f"  [{api.index}] {api.name} devices={api.device_count}")

        input_dev = manager.preferred_input_device()
        output_dev = manager.preferred_output_device()
        lines.append("")
        lines.append(f"Preferred input: {input_dev.index if input_dev else 'none'} — {input_dev.name if input_dev else 'none'}")
        lines.append(f"Preferred output: {output_dev.index if output_dev else 'none'} — {output_dev.name if output_dev else 'none'}")

        status = manager.check_stream_settings(
            samplerate=config.samplerate,
            channels=config.channels,
            input_device=input_dev.index if input_dev else None,
            output_device=output_dev.index if output_dev else None,
        )
        lines.append("")
        lines.append(f"Input settings: {status.get('input')}")
        lines.append(f"Output settings: {status.get('output')}")
    except SoundDeviceUnavailableError as exc:
        lines.append("")
        lines.append(f"sounddevice unavailable: {exc}")

    return lines


def write_audio_diagnostics_report(lines: list[str], path: str | Path) -> Path:
    """Write diagnostics lines to a timestamped text file."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat(timespec="seconds")
    content = f"generated_at: {timestamp}\n" + "\n".join(lines) + "\n"
    output_path.write_text(content, encoding="utf-8")
    return output_path

