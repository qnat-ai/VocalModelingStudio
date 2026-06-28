from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.cli.batch_runner import collect_input_files, run_batch
from app.core.pipeline import VocalPipeline
from app.utils.config import load_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Vocal Modeling Studio MVP")
    parser.add_argument("--input", default=None, help="Ścieżka do pliku WAV/MP3 z wokalem")
    parser.add_argument("--input-dir", default=None, help="Folder z plikami audio do batch processing")
    parser.add_argument("--recursive", action="store_true", help="Skanuj podfoldery przy --input-dir")
    parser.add_argument("--pattern", default="*", help="Pattern glob dla --input-dir, np. '*.wav'")
    parser.add_argument("--batch-limit", type=int, default=0, help="Limit liczby plików batch (0 = bez limitu)")
    parser.add_argument("--continue-on-error", action="store_true", help="Kontynuuj batch mimo błędów pojedynczych plików")
    parser.add_argument("--batch-summary-json", default=None, help="Opcjonalna ścieżka JSON z podsumowaniem batch")
    parser.add_argument("--reference", default=None, help="Opcjonalna próbka głosu docelowego")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--audacity-export", action="store_true", help="Eksport pliku roboczego dla Audacity")
    args = parser.parse_args()
    if bool(args.input) == bool(args.input_dir):
        parser.error("Podaj dokładnie jedno: --input albo --input-dir")
    if args.batch_limit < 0:
        parser.error("--batch-limit nie może być ujemny")
    return args


def main() -> None:
    args = parse_args()
    config = load_config(Path(args.config))
    pipeline = VocalPipeline(config=config)

    if args.input:
        result = pipeline.run(
            input_path=Path(args.input),
            reference_path=Path(args.reference) if args.reference else None,
            export_for_audacity=args.audacity_export,
        )
        print(f"Gotowe: {result}")
        return

    input_files = collect_input_files(
        Path(args.input_dir),
        recursive=bool(args.recursive),
        pattern=args.pattern,
    )
    if args.batch_limit > 0:
        input_files = input_files[: args.batch_limit]
    if not input_files:
        raise ValueError("Nie znaleziono plików audio dla podanych parametrów --input-dir/--pattern.")

    results = run_batch(
        pipeline,
        input_files,
        reference_path=Path(args.reference) if args.reference else None,
        export_for_audacity=bool(args.audacity_export),
        continue_on_error=bool(args.continue_on_error),
    )

    success_count = sum(1 for item in results if item.success)
    failed = [item for item in results if not item.success]
    print(f"Batch finished: {success_count}/{len(results)} successful")
    for item in failed:
        print(f"- ERROR {item.input_path}: {item.error}")

    if args.batch_summary_json:
        summary_path = Path(args.batch_summary_json)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            "total": len(results),
            "successful": success_count,
            "failed": len(failed),
            "results": [
                {
                    "input_path": str(item.input_path),
                    "success": item.success,
                    "output_path": str(item.output_path) if item.output_path else None,
                    "elapsed_sec": item.elapsed_sec,
                    "error": item.error,
                }
                for item in results
            ],
        }
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Batch summary JSON: {summary_path}")


if __name__ == "__main__":
    main()
