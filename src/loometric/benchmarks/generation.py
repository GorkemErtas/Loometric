"""Versioned deterministic synthetic instances using unchanged validated contracts."""

import hashlib
import json
import random
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any

from loometric.planning.domain import (
    ARITHMETIC_CONTEXT,
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
)
from loometric.planning.reporting import json_value
from loometric.planning.scenario import PlanningScenario
from loometric.planning.validation import PlanningError, calendar_date, integer
from loometric.scheduling.contracts import SchedulingInstance
from loometric.scheduling.loading import instance_json as instance_json
from loometric.scheduling.resources import build_slots, eligible

GENERATOR_VERSION = "synthetic-scheduling-v1"


@dataclass(frozen=True)
class GenerationConfig:
    orders: int = 8
    lines: int = 4
    stages: int = 2
    horizon_days: int = 1
    shifts_per_day: int = 1
    compatible_lines: int = 2
    seed: int = 42
    target_load_percent: int | None = 90
    quantity_min: int = 10
    quantity_max: int = 25
    standard_min: int = 2
    standard_max: int = 5
    shift_minutes: int = 360
    break_minutes: int = 15
    downtime_minutes: int = 10
    release_spread_days: int = 0
    due_slack_days: int = 1
    priorities: tuple[int, ...] = (1, 1, 2, 2, 3)
    start_date: date = date(2030, 1, 7)

    def __post_init__(self) -> None:
        positive = (
            "orders",
            "lines",
            "stages",
            "horizon_days",
            "shifts_per_day",
            "compatible_lines",
            "quantity_min",
            "quantity_max",
            "standard_min",
            "standard_max",
            "shift_minutes",
        )
        for name in positive:
            integer(getattr(self, name), name, minimum=1)
        for name in (
            "seed",
            "break_minutes",
            "downtime_minutes",
            "release_spread_days",
            "due_slack_days",
        ):
            integer(getattr(self, name), name)
        calendar_date(self.start_date, "start_date")
        if self.target_load_percent is not None:
            integer(self.target_load_percent, "target_load_percent", minimum=1)
        if type(self.priorities) is not tuple or not self.priorities:
            raise PlanningError("INVALID_GENERATOR", "Priorities require a nonempty integer tuple.")
        for priority in self.priorities:
            integer(priority, "priority", minimum=1)
        if (
            self.stages > len(Stage)
            or self.lines < self.stages * self.compatible_lines
            or self.quantity_max < self.quantity_min
            or self.standard_max < self.standard_min
            or self.shifts_per_day > 2
            or not 300 <= self.shift_minutes <= 480
            or self.break_minutes > 30
            or self.downtime_minutes > 25
            or self.release_spread_days >= self.horizon_days
            or self.orders > 5000
            or self.lines > 100
            or self.horizon_days > 31
            or self.due_slack_days > 31
        ):
            raise PlanningError(
                "INVALID_GENERATOR", "Unsupported or inconsistent generator dimensions/ranges."
            )
        try:
            self.start_date + timedelta(days=self.horizon_days + self.due_slack_days + 1)
        except OverflowError as exc:
            raise PlanningError(
                "INVALID_GENERATOR", "Generator dates exceed the calendar range."
            ) from exc


def _interval(start: datetime, left: int, right: int) -> TimeInterval:
    return TimeInterval(start + timedelta(minutes=left), start + timedelta(minutes=right))


def generate_instance(config: GenerationConfig) -> SchedulingInstance:
    """Local RNG only; pressure rescales labor standards, never policy or capacity."""
    rng = random.Random(config.seed)
    identity = hashlib.sha256(
        json.dumps(json_value(asdict(config)), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:20]
    instance_id = f"synthetic:{GENERATOR_VERSION}:{identity}"
    stages = tuple(Stage)[: config.stages]
    styles = tuple(
        ProductStyle(
            f"STYLE-{i:02}",
            tuple(
                StageStandard(stage, Decimal(rng.randint(config.standard_min, config.standard_max)))
                for stage in stages
            ),
        )
        for i in range(3)
    )
    lines = tuple(
        ProductionLine(
            f"LINE-{i:03}", stages[i % len(stages)], rng.randint(4, 8), AvailabilityStatus.AVAILABLE
        )
        for i in range(config.lines)
    )
    profiles = tuple(
        CapacityProfile(
            f"PROFILE-{i:03}",
            line.line_id,
            config.start_date,
            rng.choice((Decimal("0.75"), Decimal("0.85"), Decimal(1))),
            "synthetic-generator-v1",
            EvidenceStatus.SYNTHETIC,
        )
        for i, line in enumerate(lines)
    )
    days = tuple(config.start_date + timedelta(days=i) for i in range(config.horizon_days))
    zone = timezone(timedelta(hours=3))
    shifts = []
    for day_index, day in enumerate(days):
        for shift_index in range(config.shifts_per_day):
            start = datetime.combine(day, time(8 + shift_index * 8), tzinfo=zone)
            breaks = tuple(
                _interval(start, offset, offset + config.break_minutes)
                for offset in (120, 240)
                if config.break_minutes
            )
            shifts.append(
                Shift(
                    f"SHIFT-{day_index:02}-{shift_index}",
                    _interval(start, 0, config.shift_minutes),
                    breaks,
                )
            )
    assignments, downtime = [], []
    for index, line in enumerate(lines):
        for shift in shifts:
            assignment_id = f"ASG-{line.line_id}-{shift.shift_id}"
            assignments.append(
                ShiftAssignment(
                    assignment_id, line.line_id, shift.shift_id, profiles[index].profile_id
                )
            )
            if config.downtime_minutes:
                offset = 180 + (index % 3) * 5
                downtime.append(
                    PlannedDowntime(
                        f"STOP-{assignment_id}",
                        assignment_id,
                        _interval(shift.interval.start, offset, offset + config.downtime_minutes),
                        "Explicit hypothetical planned stoppage",
                    )
                )
    capabilities = []
    for style_index, style in enumerate(styles):
        for stage in stages:
            stage_lines = [line for line in lines if line.stage == stage]
            for alternative in range(config.compatible_lines):
                line = stage_lines[(style_index + alternative) % len(stage_lines)]
                capabilities.append(
                    LineCapability(
                        f"CAP-{style.style_id}-{line.line_id}",
                        line.line_id,
                        style.style_id,
                        stage,
                        "Hypothetical dedicated qualified crew",
                    )
                )
    orders = []
    for index in range(config.orders):
        release = config.start_date + timedelta(days=rng.randint(0, config.release_spread_days))
        orders.append(
            ProductionOrder(
                f"ORDER-{index:04}",
                rng.choice(styles).style_id,
                rng.randint(config.quantity_min, config.quantity_max),
                rng.choice(config.priorities),
                release,
                release + timedelta(days=rng.randint(0, config.due_slack_days)),
                stages,
            )
        )
    scenario = PlanningScenario(
        instance_id,
        True,
        (
            "Entirely synthetic; structural patterns are not calibrated factory realism.",
            "Dedicated crews and efficiency/standard assumptions; no ML or protected data.",
            f"Generator {GENERATOR_VERSION}; load target {config.target_load_percent} percent.",
        ),
        styles,
        tuple(orders),
        lines,
        tuple(shifts),
        profiles,
        tuple(capabilities),
        ProductionCalendar("SYNTHETIC-CALENDAR", days, tuple(assignments), tuple(downtime), ()),
    )
    start = datetime.combine(config.start_date, time.min, tzinfo=zone)
    instance = SchedulingInstance(
        instance_id,
        scenario,
        TimeInterval(start, start + timedelta(days=config.horizon_days)),
        180,
        1,
    )
    if config.target_load_percent is not None:
        slots = build_slots(instance)
        scales = {}
        for stage in stages:
            available = sum(
                (
                    Fraction(window.minutes)
                    * slot.line.worker_count
                    * Fraction(slot.profile.assumed_efficiency)
                    for slot in slots
                    if slot.line.stage == stage
                    for window in slot.working_intervals
                ),
                Fraction(0),
            )
            demand = sum(
                (
                    Fraction(order.quantity)
                    * Fraction(
                        next(
                            style for style in styles if style.style_id == order.style_id
                        ).standard_for(stage)
                    )
                    for order in orders
                ),
                Fraction(0),
            )
            scales[stage] = available * config.target_load_percent / (100 * demand)
        with localcontext(ARITHMETIC_CONTEXT):
            styles = tuple(
                replace(
                    style,
                    standards=tuple(
                        replace(
                            standard,
                            standard_minutes_per_unit=max(
                                Decimal("0.01"),
                                (
                                    standard.standard_minutes_per_unit
                                    * Decimal(scales[standard.stage].numerator)
                                    / Decimal(scales[standard.stage].denominator)
                                ).quantize(Decimal("0.01")),
                            ),
                        )
                        for standard in style.standards
                    ),
                )
                for style in styles
            )
        instance = replace(instance, planning=replace(scenario, styles=styles))
    return instance


def static_dimensions(instance: SchedulingInstance) -> dict[str, Any]:
    slots = build_slots(instance)
    styles = {style.style_id: style for style in instance.planning.styles}
    by_stage = {}
    for stage in {line.stage for line in instance.planning.lines}:
        available = sum(
            (
                Fraction(window.minutes)
                * slot.line.worker_count
                * Fraction(slot.profile.assumed_efficiency)
                for slot in slots
                if slot.line.stage == stage
                for window in slot.working_intervals
            ),
            Fraction(0),
        )
        demand = sum(
            (
                Fraction(order.quantity) * Fraction(styles[order.style_id].standard_for(stage))
                for order in instance.planning.orders
                if stage in order.required_stages
            ),
            Fraction(0),
        )
        with localcontext(ARITHMETIC_CONTEXT):
            by_stage[str(stage)] = (
                str(
                    Decimal((demand / available).numerator)
                    / Decimal((demand / available).denominator)
                )
                if available
                else None
            )
    return {
        "orders": len(instance.planning.orders),
        "lines": len(instance.planning.lines),
        "stages": len(by_stage),
        "horizon_minutes": int(instance.horizon.minutes),
        "shifts": len(instance.planning.shifts),
        "assignments": len(slots),
        "operations": sum(len(order.required_stages) for order in instance.planning.orders),
        "working_fragments": sum(len(slot.working_intervals) for slot in slots),
        "eligible_fragment_upper_bound": sum(
            len(slot.working_intervals)
            for order in instance.planning.orders
            for stage in order.required_stages
            for slot in slots
            if eligible(instance, order, stage, slot)
        ),
        "realized_load_by_stage": dict(sorted(by_stage.items())),
    }
