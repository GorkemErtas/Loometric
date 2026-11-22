"""Local synthetic data generation and audit, without model or scheduling execution."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from loometric.synthetic_ml.audit import quality_report
from loometric.synthetic_ml.configuration import load_configuration
from loometric.synthetic_ml.generation import generate
from loometric.synthetic_ml.storage import encode, read_bundle, write_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SYNTHETIC ML data only; no training or integration."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    generation = commands.add_parser("generate")
    generation.add_argument(
        "--configuration", type=Path, default=Path("configs/synthetic_ml_v1.json")
    )
    generation.add_argument("--profile", default="development")
    generation.add_argument("--seed", type=int, default=42)
    generation.add_argument("--scenario", default="baseline")
    generation.add_argument("--output", type=Path, required=True)
    inspection = commands.add_parser("audit")
    inspection.add_argument("--dataset", type=Path, required=True)
    inspection.add_argument("--expected-fingerprint", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            config = load_configuration(args.configuration, args.profile, args.seed, args.scenario)
            config_hash = hashlib.sha256(args.configuration.read_bytes()).hexdigest()
            result = write_bundle(
                generate(config),
                config,
                args.output,
                configuration_sha256=config_hash,
                profile=args.profile,
            )
            print(json.dumps(result, sort_keys=True))
        else:
            data, config = read_bundle(args.dataset, expected_fingerprint=args.expected_fingerprint)
            if data != generate(config):
                raise ValueError("Dataset replay differs from normalized inputs.")
            sys.stdout.write(
                encode(quality_report(data, config, replay_verified=True)).decode("utf-8")
            )
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
        print(
            json.dumps(
                {
                    "status": "INVALID_INPUT",
                    "message": "Synthetic data request rejected; no existing dataset was replaced.",
                }
            ),
            file=sys.stderr,
        )
        return 2
    return 0
