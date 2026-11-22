"""Explicit local study execution/metadata inspection; no serving or reserved-test option."""

import argparse
import json
import sys
from pathlib import Path

from loometric.synthetic_training.artifacts import checked_output, inspect_artifact, publish
from loometric.synthetic_training.configuration import load_study
from loometric.synthetic_training.study import load_datasets, run_study


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EXP-006 offline synthetic training only.")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument(
        "--configuration", type=Path, default=Path("configs/synthetic_training_v1.json")
    )
    run.add_argument("--output", type=Path, required=True)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--artifact", type=Path, required=True)
    inspect.add_argument("--expected-fingerprint", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            output = checked_output(args.output)
            config = load_study(args.configuration)
            data = load_datasets(config, Path.cwd())

            def progress(value):
                print(json.dumps(value, sort_keys=True), file=sys.stderr, flush=True)

            result = run_study(config, data, progress=progress)
            receipt = publish(result, output)
        else:
            receipt = inspect_artifact(
                args.artifact, expected_fingerprint=args.expected_fingerprint
            )
        print(json.dumps(receipt, sort_keys=True))
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        print(
            json.dumps(
                {
                    "status": "INVALID_INPUT_OR_STUDY_FAILURE",
                    "message": "Offline study rejected invalid input or failed; "
                    "existing evidence was preserved.",
                }
            ),
            file=sys.stderr,
        )
        return 2
    return 0
