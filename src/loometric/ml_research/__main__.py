"""Explicit offline research run/inspection, never a serving or regeneration command."""

import argparse
import json
from pathlib import Path

from loometric.ml_research.artifacts import checked_output, inspect_research, publish
from loometric.ml_research.protocol import load_protocol
from loometric.ml_research.study import load_inputs, run_research


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline synthetic ML improvement research.")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--output", type=Path, required=True)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--artifact", type=Path, required=True)
    inspect.add_argument("--expected-fingerprint", required=True)
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            result = inspect_research(args.artifact, args.expected_fingerprint)
        else:
            directory = checked_output(args.output)
            config = load_protocol()
            datasets, contexts, original, rows = load_inputs(config)
            print(
                json.dumps({"stage": "authorized_inputs_loaded", "cases": len(datasets)}),
                flush=True,
            )
            study = run_research(
                config,
                datasets,
                contexts,
                original,
                rows,
                progress=lambda value: print(json.dumps(value, sort_keys=True), flush=True),
            )
            result = publish(study, directory)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError) as exc:
        parser.exit(
            1, f"Research failed: {type(exc).__name__}; existing artifacts were not overwritten.\n"
        )


if __name__ == "__main__":
    raise SystemExit(main())
