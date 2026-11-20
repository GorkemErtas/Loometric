"""Standalone synthetic scenario assessment; no ML, external data or service imports."""

import argparse
import json
from decimal import DecimalException
from pathlib import Path

from loometric.planning.capacity import assess_scenario
from loometric.planning.loading import load_scenario
from loometric.planning.reporting import report_to_dict
from loometric.planning.validation import PlanningError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Independent synthetic capacity assessment; not a schedule."
    )
    parser.add_argument("--scenario", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        scenario = load_scenario(args.scenario)
        if not scenario.synthetic:
            raise PlanningError(
                "SCENARIO_NOT_SYNTHETIC", "M02 CLI supports explicitly synthetic scenarios only."
            )
        result = report_to_dict(assess_scenario(scenario))
    except (PlanningError, OSError, UnicodeError, DecimalException, OverflowError) as exc:
        result = {
            "schema_version": 1,
            "status": "INVALID_SCENARIO",
            "error": {
                "code": getattr(
                    exc,
                    "code",
                    "SCENARIO_UNREADABLE" if isinstance(exc, OSError) else "INVALID_VALUE",
                ),
                "message": str(exc),
            },
        }
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0
