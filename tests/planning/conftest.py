"""Small synthetic planning fixtures, unrelated to the historical ML dataset."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from loometric.planning.domain import (
    AvailabilityStatus,
    CapacityProfile,
    EvidenceStatus,
    LineCapability,
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
from loometric.planning.scenario import PlanningScenario


def interval(start: str, end: str) -> TimeInterval:
    return TimeInterval(datetime.fromisoformat(start), datetime.fromisoformat(end))


@pytest.fixture
def planning_scenario() -> PlanningScenario:
    day = date(2030, 1, 7)
    shift = Shift(
        "day",
        interval("2030-01-07T08:00:00+03:00", "2030-01-07T16:00:00+03:00"),
        (interval("2030-01-07T12:00:00+03:00", "2030-01-07T12:30:00+03:00"),),
    )
    return PlanningScenario(
        scenario_id="synthetic:test",
        synthetic=True,
        assumptions=("Synthetic dedicated crews with the declared style/stage capabilities only.",),
        styles=(
            ProductStyle(
                "A",
                (
                    StageStandard(Stage.SEWING, Decimal(12)),
                    StageStandard(Stage.FINISHING, Decimal(4)),
                ),
            ),
        ),
        orders=(ProductionOrder("order", "A", 50, 1, day, day, (Stage.SEWING, Stage.FINISHING)),),
        lines=(
            ProductionLine("sew", Stage.SEWING, 4, AvailabilityStatus.AVAILABLE),
            ProductionLine("finish", Stage.FINISHING, 2, AvailabilityStatus.AVAILABLE),
        ),
        shifts=(shift,),
        capacity_profiles=(
            CapacityProfile(
                "p-sew", "sew", day, Decimal("0.8"), "synthetic:test", EvidenceStatus.SYNTHETIC
            ),
            CapacityProfile(
                "p-finish",
                "finish",
                day,
                Decimal("0.9"),
                "synthetic:test",
                EvidenceStatus.SYNTHETIC,
            ),
        ),
        capabilities=(
            LineCapability("c-sew", "sew", "A", Stage.SEWING, "Synthetic qualified sewing crew."),
            LineCapability(
                "c-finish", "finish", "A", Stage.FINISHING, "Synthetic qualified finishing crew."
            ),
        ),
        calendar=ProductionCalendar(
            "calendar",
            (day,),
            (
                ShiftAssignment("a-sew", "sew", "day", "p-sew"),
                ShiftAssignment("a-finish", "finish", "day", "p-finish"),
            ),
            (),
            (),
        ),
    )
