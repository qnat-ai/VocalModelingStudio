from __future__ import annotations

import argparse
from pathlib import Path

from app.audio.cleanup import CleanupSettings, process_cleanup
from app.audio.io import load_audio, save_audio
from app.mastering.chain import MasteringChain, MasteringSettings


PRESETS = {
    "wrapper_cleanup": {
        "cleanup": {
            "remove_dc_offset": True,
            "fade_ms": 5.0,
            "noise_gate_db": -55.0,
            "trim_silence_enabled": False,
            "gain_stage_target_db": -20.0,
        },
        "mastering": {
            "enable_highpass": True,
            "highpass_hz": 85.0,
            "compressor_threshold_db": -18.0,
            "compressor_ratio": 1.8,
            "limiter_ceiling_db": -1.0,
            "makeup_gain_db": 0.0,
            "adaptive_enabled": True,
            "air_amount": 0.15,
            "stereo_width": 1.05,
        },
    },
    "wrapper_broadcast_vocal": {
        "cleanup": {
            "remove_dc_offset": True,
            "fade_ms": 8.0,
            "noise_gate_db": -52.0,
            "trim_silence_enabled": True,
            "trim_silence_db": -55.0,
            "gain_stage_target_db": -19.0,
        },
        "mastering": {
            "enable_highpass": True,
            "highpass_hz": 90.0,
            "compressor_threshold_db": -20.0,
            "compressor_ratio": 2.2,
            "limiter_ceiling_db": -1.5,
            "adaptive_enabled": True,
            "air_amount": 0.2,
            "stereo_width": 1.0,
        },
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a lightweight external FX wrapper chain")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preset", default="wrapper_cleanup", choices=sorted(PRESETS))
    parser.add_argument("--sample-rate", type=int, default=48_000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profile = PRESETS[args.preset]
    audio, sr = load_audio(args.input, sample_rate=args.sample_rate, mono=False)
    audio = process_cleanup(audio, sr, CleanupSettings.from_mapping(profile["cleanup"]))
    audio = MasteringChain(MasteringSettings.from_mapping(profile["mastering"])).process_audio(audio, sr)
    save_audio(args.output, audio, sr)
    print(f"External FX wrapper wrote: {args.output}")


if __name__ == "__main__":
    main()

