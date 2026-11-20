"""Strict scheduling wire format embedding the unchanged M02 planning schema."""

import json
import re
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from loometric.planning.domain import Stage
from loometric.planning.loading import (
    enumeration,
    fields,
    items,
    parse_interval,
    parse_json,
    scenario_from_dict,
)
from loometric.planning.validation import PlanningError
from loometric.scheduling.contracts import (
    OperationAllocation,
    ProposedSchedule,
    SchedulingInstance,
    UnscheduledOperation,
    UnscheduledReason,
)


def parse_instance(source: str) -> SchedulingInstance:
    data = fields(parse_json(source), tuple(SchedulingInstance.__dataclass_fields__))
    return SchedulingInstance(
        instance_id=data["instance_id"],
        planning=scenario_from_dict(data["planning"]),
        horizon=parse_interval(data["horizon"]),
        calendar_utc_offset_minutes=data["calendar_utc_offset_minutes"],
        allocation_granularity_minutes=data["allocation_granularity_minutes"],
        schema_version=data["schema_version"],
        policy_version=data["policy_version"],
    )


def _reported_decimal(value: object) -> Decimal:
    if not isinstance(value, str) or not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value):
        raise PlanningError(
            "INVALID_REPORTED_DECIMAL",
            "Proposal labor/capacity fields require nonnegative decimal strings.",
        )
    return Decimal(value)


def parse_schedule(source: str) -> ProposedSchedule:
    data = fields(parse_json(source), tuple(ProposedSchedule.__dataclass_fields__))
    allocations = []
    for raw in items(data["allocations"]):
        raw = fields(raw, tuple(OperationAllocation.__dataclass_fields__))
        allocations.append(
            OperationAllocation(
                **{
                    **raw,
                    "stage": enumeration(Stage, raw["stage"]),
                    "interval": parse_interval(raw["interval"]),
                    **{
                        name: _reported_decimal(raw[name])
                        for name in (
                            "required_standard_minutes",
                            "consumed_worker_minutes",
                            "consumed_standard_minutes",
                        )
                    },
                }
            )
        )
    unscheduled = []
    for raw in items(data["unscheduled"]):
        raw = fields(raw, tuple(UnscheduledOperation.__dataclass_fields__))
        unscheduled.append(
            UnscheduledOperation(
                **{
                    **raw,
                    "stage": enumeration(Stage, raw["stage"]),
                    "reason": enumeration(UnscheduledReason, raw["reason"]),
                }
            )
        )
    return ProposedSchedule(
        **{**data, "allocations": tuple(allocations), "unscheduled": tuple(unscheduled)}
    )


def load_instance(path: Path) -> SchedulingInstance:
    return parse_instance(path.read_text(encoding="utf-8"))


def load_schedule(path: Path) -> ProposedSchedule:
    return parse_schedule(path.read_text(encoding="utf-8"))


def instance_json(instance: SchedulingInstance) -> str:
    """Lossless input JSON: planning decimals are numeric tokens, not report strings."""

    def encode(value: Any) -> str:
        if isinstance(value, Decimal):
            if not value.is_finite():
                raise ValueError("Nonfinite instance decimal")
            return format(value, "f")
        if isinstance(value, (datetime, date)):
            return json.dumps(value.isoformat())
        if isinstance(value, dict):
            return (
                "{"
                + ",".join(
                    json.dumps(key) + ":" + encode(item) for key, item in sorted(value.items())
                )
                + "}"
            )
        if isinstance(value, (list, tuple)):
            return "[" + ",".join(encode(item) for item in value) + "]"
        return json.dumps(value, allow_nan=False)

    return encode(asdict(instance)) + "\n"
