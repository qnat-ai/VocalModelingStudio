"""Probe a running Applio (Gradio) instance and report its real API surface.

Applio exposes its UI through Gradio, and Gradio auto-generates a REST/RPC
API for every named endpoint. The exact endpoint name and parameter order
depend on the Applio version and how its UI is built internally, and this
is not reliably documented anywhere stable enough to hard-code. Rather than
guessing, run this tool against your own local Applio instance to see the
real, current contract.

Usage:
    1. Start Applio (e.g. run-applio.bat) and note the URL it prints,
       typically http://127.0.0.1:7860
    2. python tools/applio_probe.py --url http://127.0.0.1:7860
    3. python tools/applio_probe.py --url http://127.0.0.1:7860 --json

This only inspects the API; it does not submit any conversion job.
"""

from __future__ import annotations

import argparse
import json
import sys


def probe(url: str) -> dict:
    try:
        from gradio_client import Client
    except ImportError as exc:  # pragma: no cover - exercised only without the optional dependency
        raise SystemExit(
            "gradio_client is not installed. Install it with:\n"
            "    pip install gradio_client\n"
            "(This is a separate, optional dependency from the main project requirements.txt,"
            " only needed for talking to a running Applio/Gradio instance.)"
        ) from exc

    client = Client(url)
    api_info = client.view_api(print_info=False, return_format="dict")
    return api_info


def summarize(api_info: dict) -> str:
    lines: list[str] = []
    named = api_info.get("named_endpoints", {})
    unnamed = api_info.get("unnamed_endpoints", {})

    lines.append(f"Named endpoints: {len(named)}")
    for name, spec in named.items():
        params = spec.get("parameters", [])
        returns = spec.get("returns", [])
        lines.append(f"\n  {name}")
        lines.append("    parameters:")
        for p in params:
            label = p.get("label") or p.get("parameter_name") or "?"
            ptype = p.get("python_type", {}).get("type", "?")
            default = p.get("parameter_default", "<required>")
            lines.append(f"      - {label} ({ptype}), default={default!r}")
        lines.append("    returns:")
        for r in returns:
            label = r.get("label") or "?"
            rtype = r.get("python_type", {}).get("type", "?")
            lines.append(f"      - {label} ({rtype})")

    if unnamed:
        lines.append(f"\nUnnamed endpoints: {len(unnamed)} (use --all to inspect with view_api(all_endpoints=True) manually)")

    if not named and not unnamed:
        lines.append(
            "\nNo endpoints reported. The instance may have disabled its API, "
            "or this client/server version mismatch is hiding it. "
            "Open the app in a browser and check the 'Use via API' link in the footer."
        )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe a running Applio (Gradio) instance's API surface.")
    parser.add_argument("--url", required=True, help="Base URL of the running Applio instance, e.g. http://127.0.0.1:7860")
    parser.add_argument("--json", action="store_true", help="Print the raw API info as JSON instead of a summary.")
    args = parser.parse_args()

    try:
        api_info = probe(args.url)
    except Exception as exc:  # noqa: BLE001 - this is a diagnostic CLI tool, surface any failure to the user
        print(f"ERROR: Could not retrieve API info from {args.url}: {exc}", file=sys.stderr)
        print(
            "Check that Applio is running and that the URL matches what its console printed "
            "(it may differ from the default if the port was already in use).",
            file=sys.stderr,
        )
        return 1

    if args.json:
        print(json.dumps(api_info, indent=2, ensure_ascii=False, default=str))
    else:
        print(summarize(api_info))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
