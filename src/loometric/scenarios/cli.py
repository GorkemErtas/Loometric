"""Offline baseline/specification comparison; greedy has no optional solver dependency."""

import argparse
import json
from decimal import DecimalException
from pathlib import Path

from loometric.planning.validation import PlanningError
from loometric.scenarios.engine import compare_scenario
from loometric.scenarios.loading import load_specification
from loometric.scheduling.loading import load_instance


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Conditional synthetic production what-if comparison."
    )
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--scenario", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = compare_scenario(load_instance(args.baseline), load_specification(args.scenario))
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0
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
