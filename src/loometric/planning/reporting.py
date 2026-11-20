"""Deterministic JSON-compatible reports with explicit decimal strings."""

from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from loometric.planning.capacity import PlanningReport


def json_value(value: Any) -> Any:
    """Shared standard-library wire values for planning and scheduling reports."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        result = format(value, "f")
        return result.rstrip("0").rstrip(".") if "." in result else result
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_value(item) for item in value]
    return value


def report_to_dict(report: PlanningReport) -> dict[str, Any]:
    return json_value(asdict(report))
