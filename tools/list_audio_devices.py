"""List audio devices visible to sounddevice/PortAudio.

Usage:
    python tools/list_audio_devices.py
    python tools/list_audio_devices.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.audio_devices.device_manager import AudioDeviceManager, SoundDeviceUnavailableError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="List audio devices visible to sounddevice/PortAudio.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    try:
        manager = AudioDeviceManager()
        hostapis = manager.query_hostapis()
        devices = manager.query_devices()
    except SoundDeviceUnavailableError as exc:
        print(f"ERROR: {exc}")
        return 2

    if args.json:
        print(json.dumps({"hostapis": [asdict(x) for x in hostapis], "devices": [asdict(x) for x in devices]}, indent=2, ensure_ascii=False))
        return 0

    print("Host APIs:")
    for api in hostapis:
        print(f"  [{api.index}] {api.name} devices={api.device_count}")

    print("\nDevices:")
    for dev in devices:
        io = []
        if dev.can_input:
            io.append(f"in={dev.max_input_channels}")
        if dev.can_output:
            io.append(f"out={dev.max_output_channels}")
        print(f"  [{dev.index}] {dev.name} | {dev.hostapi_name} | {' '.join(io)} | {dev.default_samplerate:.0f} Hz")

    preferred_input = manager.preferred_input_device()
    preferred_output = manager.preferred_output_device()
    print("\nPreferred:")
    print(f"  input:  {preferred_input.index if preferred_input else 'none'} — {preferred_input.name if preferred_input else 'none'}")
    print(f"  output: {preferred_output.index if preferred_output else 'none'} — {preferred_output.name if preferred_output else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
