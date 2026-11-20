"""Local reference scheduling or arbitrary proposal verification; no solver or services."""

import argparse
import json
from dataclasses import asdict
from decimal import DecimalException
from pathlib import Path

from loometric.planning.reporting import json_value
from loometric.planning.validation import PlanningError
from loometric.scheduling.contracts import instance_fingerprint
from loometric.scheduling.dispatcher import ALGORITHM, dispatch
from loometric.scheduling.loading import load_instance, load_schedule
from loometric.scheduling.metrics import calculate_metrics
from loometric.scheduling.verification import verify_schedule


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Synthetic whole-stage scheduling and independent verification."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("dispatch", "verify"):
        sub = commands.add_parser(command)
        sub.add_argument("--instance", type=Path, required=True)
        if command == "verify":
            sub.add_argument("--schedule", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        instance = load_instance(args.instance)
        if not instance.planning.synthetic:
            raise PlanningError(
                "INSTANCE_NOT_SYNTHETIC", "M03A CLI accepts explicitly synthetic instances only."
            )
        schedule = (
            dispatch(instance) if args.command == "dispatch" else load_schedule(args.schedule)
        )
        verification = verify_schedule(instance, schedule)
        metrics = calculate_metrics(instance, schedule) if verification.feasible else None
        result = {
            "schema_version": 1,
            "policy_version": instance.policy_version,
            "instance_id": instance.instance_id,
            "instance_fingerprint": instance_fingerprint(instance),
            "synthetic": True,
            "algorithm": ALGORITHM if args.command == "dispatch" else "EXTERNAL_PROPOSAL",
            "optimality_claim": False,
            "status": verification.status,
            "assumptions": instance.planning.assumptions,
            "horizon": asdict(instance.horizon),
            "calendar_utc_offset_minutes": instance.calendar_utc_offset_minutes,
            "allocation_granularity_minutes": instance.allocation_granularity_minutes,
            "schedule": asdict(schedule),
            "verification": asdict(verification),
            "metrics": asdict(metrics) if metrics is not None else None,
        }
        print(json.dumps(json_value(result), indent=2, sort_keys=True, allow_nan=False))
        return 0 if verification.feasible else 2
    except (PlanningError, OSError, UnicodeError, DecimalException, OverflowError) as exc:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "INVALID_INPUT",
                    "metrics": None,
                    "error": {
                        "code": getattr(
                            exc,
                            "code",
                            "INPUT_UNREADABLE" if isinstance(exc, OSError) else "INVALID_VALUE",
                        ),
                        "message": str(exc),
                    },
                },
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
        )
        return 2
