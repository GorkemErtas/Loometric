from dataclasses import replace
from decimal import Decimal, localcontext
from pathlib import Path

import pytest

from loometric.synthetic_ml.configuration import GenerationConfig, load_configuration
from loometric.synthetic_ml.contracts import target_value


def test_target_units_overachievement_zero_capacity_and_rounding():
    assert target_value(60, Decimal("2.5"), 100) == ("VALID", Decimal("1.5"))
    assert target_value(0, Decimal("2.5"), 100) == ("VALID", Decimal(0))
    assert target_value(0, Decimal("2.5"), 0) == ("ZERO_PLANNED_CAPACITY", None)
    with localcontext() as context:
        context.prec = 3
        assert target_value(1, Decimal(1), 3)[1] == Decimal("0.3333333333333333333333333333")


@pytest.mark.parametrize(
    "args",
    [
        (-1, Decimal(1), 1),
        (1, Decimal(1), 0),
        (1, Decimal(0), 1),
        (1, Decimal("NaN"), 1),
        (1, Decimal("Infinity"), 1),
        (True, Decimal(1), 1),
        (1, 1.5, 1),
        (1, Decimal(1), -1),
    ],
)
def test_invalid_labels_reject_instead_of_imputing_or_clipping(args):
    with pytest.raises(ValueError):
        target_value(*args)


@pytest.mark.parametrize(
    "changes",
    [
        {"seed": True},
        {"calendar_days": 10},
        {"workers_min": 20, "workers_max": 10},
        {"scenario": "real_factory"},
        {"label_delay_minutes": 721},
        {"embargo_dates": -1},
        {"styles": 1},
        {"standard_hundredths_min": 0},
        {"process_noise_bps": 10000},
        {"calendar_days": 730, "factories": 8, "lines_per_stage": 4},
    ],
)
def test_bounded_configuration_rejects_bad_or_expensive_requests(changes):
    with pytest.raises(ValueError):
        replace(GenerationConfig(), **changes)


def test_declared_multiple_seeds_sizes_and_shift_scenarios():
    path = Path(__file__).resolve().parents[2] / "configs/synthetic_ml_v1.json"
    for seed in (19, 42, 73):
        for scenario in ("baseline", "disruption", "workload_surge"):
            small = load_configuration(path, "development", seed, scenario)
            large = load_configuration(path, "benchmark", seed, scenario)
            assert large.calendar_days > small.calendar_days
            assert small.seed == seed and small.scenario == scenario
