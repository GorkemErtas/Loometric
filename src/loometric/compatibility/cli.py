"""Explicit local compatibility/retrospective inspection commands, no HTTP or prediction."""

import argparse
import json
import sys
from pathlib import Path

from loometric.compatibility.assessment import assess_compatibility
from loometric.compatibility.contracts import AssessmentRequest


def _read(path: Path, max_bytes: int = 262144) -> str:
    with path.open("rb") as source:
        value = source.read(max_bytes + 1)
    if len(value) > max_bytes:
        raise ValueError("Local input exceeds the byte limit.")
    return value.decode("utf-8", errors="strict")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="M07B offline audit; never authorizes capacity changes."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    assessment = commands.add_parser(
        "assess", help="Assess declared context, without model execution."
    )
    assessment.add_argument("--request", type=Path, required=True)
    assessment.add_argument("--instance", type=Path, required=True)
    assessment.add_argument("--artifact", type=Path, required=True)
    assessment.add_argument("--expected-fingerprint", required=True)
    assessment.add_argument("--output", type=Path)
    inspection = commands.add_parser(
        "inspect-saved", help="Inspect saved EXP-004 training-period OOF predictions."
    )
    inspection.add_argument(
        "--dataset", type=Path, default=Path("data/raw/garments_worker_productivity.csv")
    )
    inspection.add_argument(
        "--split-config", type=Path, default=Path("configs/chronological_split.json")
    )
    inspection.add_argument(
        "--predictions", type=Path, default=Path("data/processed/exp-004-temporal-robustness.json")
    )
    inspection.add_argument("--expected-predictions-sha256", required=True)
    inspection.add_argument(
        "--include-observations",
        action="store_true",
        help="Include authorized inner-OOF targets/predictions in the local report.",
    )
    inspection.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        # Refuse overwrite before reading source labels or artifact bytes.
        if args.output is not None and args.output.exists():
            raise ValueError("Output already exists; choose a new path.")
        if args.command == "assess":
            from loometric.compatibility.artifacts import inspect_model_profile
            from loometric.compatibility.contracts import bounded_json
            from loometric.scheduling.loading import parse_instance

            request = AssessmentRequest.from_json(_read(args.request))
            instance_source = _read(args.instance)
            bounded_json(instance_source)
            instance = parse_instance(instance_source)
            if not instance.planning.synthetic:
                raise ValueError("M07B planning contexts must be explicitly synthetic.")
            model = inspect_model_profile(
                args.artifact, expected_fingerprint=args.expected_fingerprint
            )
            result = assess_compatibility(request, model, instance).to_dict()
        else:
            from loometric.compatibility.inspection import inspect_saved_predictions

            result = inspect_saved_predictions(
                args.dataset,
                args.split_config,
                args.predictions,
                expected_predictions_sha256=args.expected_predictions_sha256,
                include_observations=args.include_observations,
            )
        encoded = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
        if args.output is None:
            sys.stdout.write(encoded)
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8", newline="\n") as destination:
                destination.write(encoded)
            receipt = {"status": "AUDIT_WRITTEN", "capacity_application_authorized": False}
            print(json.dumps(receipt))
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        print(
            json.dumps(
                {
                    "status": "INVALID_INPUT",
                    "message": "Offline audit rejected missing or inconsistent input. "
                    "No prediction or conversion was performed.",
                }
            ),
            file=sys.stderr,
        )
        return 2
    return 0
