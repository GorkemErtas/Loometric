"""Synthetic scheduling fixtures derived only from the versioned M02 example."""

from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest

from loometric.planning.domain import TimeInterval
from loometric.planning.loading import load_scenario
from loometric.scheduling.contracts import SchedulingInstance

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def scheduling_instance() -> SchedulingInstance:
    source = load_scenario(ROOT / "examples/planning/capacity-demo.json")
    line_ids = {"SEW-01", "FIN-01"}
    planning = replace(
        source,
        scenario_id="synthetic:scheduling-test",
        styles=(source.styles[0],),
        orders=(
            replace(source.orders[0], order_id="A", quantity=60, priority=1),
            replace(source.orders[1], order_id="B", quantity=80, priority=2),
        ),
        lines=tuple(line for line in source.lines if line.line_id in line_ids),
        shifts=(replace(source.shifts[0], breaks=()),),
        capacity_profiles=tuple(p for p in source.capacity_profiles if p.line_id in line_ids),
        capabilities=tuple(c for c in source.capabilities if c.line_id in line_ids),
        calendar=replace(
            source.calendar,
            assignments=tuple(
                a
                for a in source.calendar.assignments
                if a.line_id in line_ids and a.shift_id == "DAY"
            ),
            planned_downtime=(),
            unavailable_periods=(),
        ),
    )
    return SchedulingInstance(
        "synthetic:reference-test",
        planning,
        TimeInterval(
            datetime.fromisoformat("2030-01-07T08:00:00+03:00"),
            datetime.fromisoformat("2030-01-07T16:00:00+03:00"),
        ),
        180,
        1,
    )
