"""Test low-latency input-to-output monitoring.

This tool is intentionally simple. It is meant to validate device selection and
latency profiles, not to run heavy AI processing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.realtime.config import load_realtime_config  # noqa: E402
from app.realtime.diagnostics import build_audio_diagnostics_report, write_audio_diagnostics_report  # noqa: E402
from app.realtime.low_latency_stream import LowLatencyMonitor  # noqa: E402
from app.audio_devices.device_manager import SoundDeviceUnavailableError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a short low-latency monitoring test.")
    parser.add_argument("--profile", default=None, help="safe, balanced, low, realtime_experimental")
    parser.add_argument("--seconds", type=float, default=5.0, help="How long to run the stream.")
    parser.add_argument("--dry-run", action="store_true", help="Only print diagnostics; do not open the stream.")
    parser.add_argument("--save-report", default="logs/audio_diagnostics.txt", help="Path for diagnostics report output.")
    parser.add_argument("--input-device", type=int, default=None, help="Input device index from list_audio_devices.py")
    parser.add_argument("--output-device", type=int, default=None, help="Output device index from list_audio_devices.py")
    args = parser.parse_args()

    config = load_realtime_config(profile_name=args.profile)
    report_lines = build_audio_diagnostics_report(config)
    print("\n".join(report_lines))
    report_path = write_audio_diagnostics_report(report_lines, args.save_report)
    print(f"\nDiagnostics report saved: {report_path}")

    if args.dry_run:
        return 0

    print("\nStarting monitor. Use headphones and keep volume low to avoid feedback.")
    try:
        monitor = LowLatencyMonitor(config, input_device=args.input_device, output_device=args.output_device)
        stats = monitor.run_for_seconds(args.seconds)
    except SoundDeviceUnavailableError as exc:
        print(f"ERROR: {exc}")
        return 2
    except Exception as exc:
        print(f"ERROR while opening audio stream: {exc}")
        return 3

    print("\nFinished.")
    print(f"callbacks: {stats.callbacks}")
    print(f"overflows: {stats.overflows}")
    print(f"underflows: {stats.underflows}")
    if stats.last_status:
        print(f"last status: {stats.last_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
