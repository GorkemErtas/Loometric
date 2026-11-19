"""Local-only train/predict commands; JSON results and no implicit training."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from loometric.prediction.artifacts import generate_artifact, load_artifact
from loometric.prediction.contracts import (
    ContractError,
    PredictionRequest,
    Warning,
    read_json,
    timestamp,
)
from loometric.prediction.inference import make_result, predict
from loometric.prediction.policy import ReviewPolicy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Experimental local offline prediction; no decision approval."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    train = commands.add_parser(
        "train", help="Explicitly generate a training-partition-only artifact."
    )
    train.add_argument(
        "--dataset", type=Path, default=Path("data/raw/garments_worker_productivity.csv")
    )
    train.add_argument("--split", type=Path, default=Path("configs/chronological_split.json"))
    train.add_argument(
        "--artifact", type=Path, required=True, help="New directory; never overwritten."
    )
    forecast = commands.add_parser(
        "predict", help="Load a trusted local artifact and validate a JSON request."
    )
    forecast.add_argument("--artifact", type=Path, required=True)
    forecast.add_argument(
        "--expected-fingerprint",
        required=True,
        help="Digest retained from trusted training output.",
    )
    forecast.add_argument("--request", type=Path, required=True)
    forecast.add_argument("--policy", type=Path)
    forecast.add_argument(
        "--at",
        help="Explicit offline replay reference time; actual execution time is also returned.",
    )
    args = parser.parse_args(argv)
    if args.command == "train":
        try:
            generated = generate_artifact(args.dataset, args.split, args.artifact)
            print(
                json.dumps(
                    {
                        "artifact_fingerprint": generated["artifact_fingerprint"],
                        "artifact_directory": str(args.artifact),
                        "model_configuration_fingerprint": generated["manifest"][
                            "model_configuration_fingerprint"
                        ],
                        "lineage": generated["manifest"]["lineage"],
                    },
                    indent=2,
                    allow_nan=False,
                )
            )
            return 0
        except (OSError, ValueError) as exc:
            print(json.dumps({"error": "ARTIFACT_GENERATION_FAILED", "message": str(exc)}))
            return 2
    now = datetime.now(UTC)
    request = None
    replay_at = None
    try:
        replay_at = timestamp(args.at) if args.at is not None else None
        request = PredictionRequest.from_dict(read_json(args.request.read_text(encoding="utf-8")))
        policy = (
            ReviewPolicy.from_dict(read_json(args.policy.read_text(encoding="utf-8")))
            if args.policy
            else ReviewPolicy()
        )
        artifact = load_artifact(args.artifact, expected_fingerprint=args.expected_fingerprint)
        result = predict(request, artifact, now=now, policy=policy, replay_at=replay_at)
    except (ContractError, OSError, UnicodeError) as exc:
        result = make_result(
            now=now,
            request=request,
            replay_at=replay_at,
            warnings=(Warning(getattr(exc, "code", "INPUT_UNAVAILABLE"), str(exc)),),
        )
    print(json.dumps(result.to_dict(), indent=2, allow_nan=False))
    return 2 if result.status == "ABSTAIN" else 0
