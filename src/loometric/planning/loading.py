"""Strict, versioned planning JSON; no factory data, ML imports or model artifacts."""

import json
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, TypeVar

from loometric.planning.domain import (
    AvailabilityStatus,
    CapacityProfile,
    EvidenceStatus,
    LineCapability,
    PlannedDowntime,
    ProductionCalendar,
    ProductionLine,
    ProductionOrder,
    ProductStyle,
    Shift,
    ShiftAssignment,
    Stage,
    StageStandard,
    TimeInterval,
    UnavailablePeriod,
)
from loometric.planning.scenario import PlanningScenario
from loometric.planning.validation import PlanningError


def fields(value: Any, required: tuple[str, ...], optional: tuple[str, ...] = ()) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PlanningError("INVALID_OBJECT", "Expected a planning JSON object.")
    missing, extra = set(required) - set(value), set(value) - set(required) - set(optional)
    if missing or extra:
        raise PlanningError(
            "INVALID_FIELDS",
            f"Missing fields {sorted(missing)}; unsupported fields {sorted(extra)}.",
        )
    return value


def items(value: Any) -> list[Any]:
    if not isinstance(value, list):
        raise PlanningError("INVALID_COLLECTION", "Planning collections must be JSON arrays.")
    return value


def number(value: Any) -> Decimal:
    if type(value) is int:
        return Decimal(value)
    if isinstance(value, Decimal):
        return value
    raise PlanningError(
        "INVALID_DECIMAL", "Use a JSON number, not a string, boolean or binary float."
    )


def parse_date(value: Any) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise PlanningError("INVALID_DATE", "Planning dates require YYYY-MM-DD.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise PlanningError("INVALID_DATE", "Invalid planning calendar date.") from exc


def parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?"
        r"(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])",
        value,
    ):
        raise PlanningError(
            "INVALID_TIMESTAMP", "Use ISO timestamps with seconds and a timezone offset."
        )
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise PlanningError("INVALID_TIMESTAMP", "Invalid planning timestamp.") from exc


def parse_interval(value: Any) -> TimeInterval:
    value = fields(value, ("start", "end"))
    return TimeInterval(parse_timestamp(value["start"]), parse_timestamp(value["end"]))


E = TypeVar("E", Stage, AvailabilityStatus, EvidenceStatus)


def enumeration(enum_type: type[E], value: Any) -> E:
    try:
        return enum_type(value)
    except (ValueError, TypeError) as exc:
        raise PlanningError("INVALID_ENUM", f"Unsupported {enum_type.__name__} value.") from exc


def parse_scenario(source: str) -> PlanningScenario:
    """Parse once with Decimal numbers; reject duplicate keys and nonstandard constants."""

    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise PlanningError("DUPLICATE_JSON_KEY", f"Duplicate key: {key}")
            result[key] = value
        return result

    def invalid_constant(_: str) -> None:
        raise PlanningError("INVALID_JSON", "Nonfinite JSON constants are unsupported.")

    try:
        data = json.loads(
            source,
            parse_float=Decimal,
            object_pairs_hook=unique_pairs,
            parse_constant=invalid_constant,
        )
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, PlanningError):
            raise
        raise PlanningError("INVALID_JSON", "Malformed planning JSON.") from exc
    data = fields(
        data,
        (
            "schema_version",
            "scenario_id",
            "synthetic",
            "assumptions",
            "styles",
            "orders",
            "lines",
            "shifts",
            "capacity_profiles",
            "capabilities",
            "calendar",
        ),
    )
    styles = []
    for raw in items(data["styles"]):
        raw = fields(raw, ("style_id", "standards", "output_unit"))
        standards = []
        for standard in items(raw["standards"]):
            standard = fields(standard, ("stage", "standard_minutes_per_unit", "measurement_unit"))
            standards.append(
                StageStandard(
                    enumeration(Stage, standard["stage"]),
                    number(standard["standard_minutes_per_unit"]),
                    standard["measurement_unit"],
                )
            )
        styles.append(ProductStyle(raw["style_id"], tuple(standards), raw["output_unit"]))
    orders = []
    for raw in items(data["orders"]):
        raw = fields(
            raw,
            (
                "order_id",
                "style_id",
                "quantity",
                "priority",
                "release_date",
                "due_date",
                "required_stages",
            ),
        )
        orders.append(
            ProductionOrder(
                raw["order_id"],
                raw["style_id"],
                raw["quantity"],
                raw["priority"],
                parse_date(raw["release_date"]),
                parse_date(raw["due_date"]),
                tuple(enumeration(Stage, stage) for stage in items(raw["required_stages"])),
            )
        )
    lines = []
    for raw in items(data["lines"]):
        raw = fields(raw, ("line_id", "stage", "worker_count", "availability"))
        lines.append(
            ProductionLine(
                raw["line_id"],
                enumeration(Stage, raw["stage"]),
                raw["worker_count"],
                enumeration(AvailabilityStatus, raw["availability"]),
            )
        )
    shifts = []
    for raw in items(data["shifts"]):
        raw = fields(raw, ("shift_id", "interval", "breaks"))
        shifts.append(
            Shift(
                raw["shift_id"],
                parse_interval(raw["interval"]),
                tuple(parse_interval(interval) for interval in items(raw["breaks"])),
            )
        )
    profiles = []
    for raw in items(data["capacity_profiles"]):
        raw = fields(
            raw,
            (
                "profile_id",
                "line_id",
                "effective_date",
                "assumed_efficiency",
                "source_id",
                "evidence_status",
            ),
            ("evidence_reference",),
        )
        profiles.append(
            CapacityProfile(
                raw["profile_id"],
                raw["line_id"],
                parse_date(raw["effective_date"]),
                number(raw["assumed_efficiency"]),
                raw["source_id"],
                enumeration(EvidenceStatus, raw["evidence_status"]),
                raw.get("evidence_reference"),
            )
        )
    capabilities = []
    for raw in items(data["capabilities"]):
        raw = fields(raw, ("capability_id", "line_id", "style_id", "stage", "workforce_basis"))
        capabilities.append(
            LineCapability(
                raw["capability_id"],
                raw["line_id"],
                raw["style_id"],
                enumeration(Stage, raw["stage"]),
                raw["workforce_basis"],
            )
        )
    raw_calendar = fields(
        data["calendar"],
        ("calendar_id", "working_dates", "assignments", "planned_downtime", "unavailable_periods"),
    )
    assignments = []
    for raw in items(raw_calendar["assignments"]):
        raw = fields(raw, ("assignment_id", "line_id", "shift_id", "profile_id"))
        assignments.append(ShiftAssignment(**raw))
    downtime = []
    for raw in items(raw_calendar["planned_downtime"]):
        raw = fields(raw, ("downtime_id", "assignment_id", "interval", "reason"))
        downtime.append(
            PlannedDowntime(
                raw["downtime_id"],
                raw["assignment_id"],
                parse_interval(raw["interval"]),
                raw["reason"],
            )
        )
    unavailable = []
    for raw in items(raw_calendar["unavailable_periods"]):
        raw = fields(raw, ("period_id", "line_id", "interval", "reason"))
        unavailable.append(
            UnavailablePeriod(
                raw["period_id"], raw["line_id"], parse_interval(raw["interval"]), raw["reason"]
            )
        )
    calendar = ProductionCalendar(
        raw_calendar["calendar_id"],
        tuple(parse_date(day) for day in items(raw_calendar["working_dates"])),
        tuple(assignments),
        tuple(downtime),
        tuple(unavailable),
    )
    return PlanningScenario(
        data["scenario_id"],
        data["synthetic"],
        tuple(items(data["assumptions"])),
        tuple(styles),
        tuple(orders),
        tuple(lines),
        tuple(shifts),
        tuple(profiles),
        tuple(capabilities),
        calendar,
        data["schema_version"],
    )


def load_scenario(path: Path) -> PlanningScenario:
    return parse_scenario(path.read_text(encoding="utf-8"))
