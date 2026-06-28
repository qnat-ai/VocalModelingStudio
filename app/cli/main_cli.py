"""CLI entry point for Vocal Modeling Studio."""
from __future__ import annotations

import argparse
from pathlib import Path

from app.core.pipeline import VocalPipeline
from app.utils.config import load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vocal Modeling Studio CLI")
    parser.add_argument("input", type=Path, help="Input WAV/MP3 file")
    parser.add_argument("--output", type=Path, default=Path("examples/output/output.wav"))
    parser.add_argument("--reference", type=Path, default=None, help="Reference voice sample")
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"), help="YAML config path")
    parser.add_argument("--audacity-export", action="store_true", help="Export a working copy for Audacity")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    pipeline = VocalPipeline(config=config)
    if args.dry_run:
        print(f"DRY RUN: {args.input} -> {args.output}")
        return
    result = pipeline.run(
        input_path=args.input,
        output_path=args.output,
        reference_path=args.reference,
        export_for_audacity=args.audacity_export,
    )
    print(f"Gotowe: {result}")


if __name__ == "__main__":
    main()
