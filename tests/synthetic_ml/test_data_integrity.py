from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from loometric.synthetic_ml.generation import generate
from loometric.synthetic_ml.validation import validate_dataset


@pytest.mark.parametrize(
    "kind",
    [
        "missing_standard",
        "duplicate",
        "foreign_key",
        "qualification",
        "style",
        "planned_workers",
        "actual_workers",
        "negative_quantity",
        "missing_quantity",
        "invalid_standard",
        "nonfinite_standard",
        "snapshot",
        "reference_timing",
        "label_timing",
        "production_balance",
        "zero_capacity_production",
        "physical_envelope",
        "wrong_partition",
        "wrong_population",
        "wrong_calendar",
        "duplicate_crew_slot",
        "loss_exceeds_minutes",
        "bool_count",
    ],
)
def test_malformed_or_inconsistent_data_is_rejected(synthetic_data, synthetic_config, kind):
    data = synthetic_data
    plan, outcome = data.plans[0], data.outcomes[0]
    if kind == "missing_standard":
        data = replace(data, standards=data.standards[1:])
    elif kind == "duplicate":
        data = replace(data, plans=(*data.plans, plan))
    elif kind == "foreign_key":
        data = replace(data, plans=(replace(plan, line_id="unknown"), *data.plans[1:]))
    elif kind == "qualification":
        crew = next(c for c in data.crews if c.crew_id == plan.crew_id)
        data = replace(
            data,
            crews=tuple(
                replace(c, line_id=data.lines[-1].line_id) if c == crew else c for c in data.crews
            ),
        )
    elif kind == "style":
        data = replace(data, orders=(replace(data.orders[0], style_id="unknown"), *data.orders[1:]))
    elif kind == "planned_workers":
        data = replace(data, plans=(replace(plan, planned_workers=10000), *data.plans[1:]))
    elif kind == "actual_workers":
        data = replace(
            data,
            outcomes=(
                replace(outcome, realized_workers=plan.planned_workers + 1),
                *data.outcomes[1:],
            ),
        )
    elif kind == "negative_quantity":
        data = replace(data, orders=(replace(data.orders[0], quantity=-1), *data.orders[1:]))
    elif kind == "missing_quantity":
        data = replace(data, orders=(replace(data.orders[0], quantity=None), *data.orders[1:]))
    elif kind in ("invalid_standard", "nonfinite_standard"):
        data = replace(
            data,
            standards=(
                replace(
                    data.standards[0],
                    worker_minutes_per_piece=Decimal(0)
                    if kind == "invalid_standard"
                    else Decimal("NaN"),
                ),
                *data.standards[1:],
            ),
        )
    elif kind == "snapshot":
        data = replace(
            data,
            plans=(replace(plan, snapshot_at=plan.cutoff + timedelta(minutes=1)), *data.plans[1:]),
        )
    elif kind == "reference_timing":
        data = replace(
            data,
            orders=(
                replace(data.orders[0], available_at=plan.cutoff + timedelta(hours=1)),
                *data.orders[1:],
            ),
        )
    elif kind == "label_timing":
        data = replace(
            data, outcomes=(replace(outcome, available_at=plan.cutoff), *data.outcomes[1:])
        )
    elif kind == "production_balance":
        data = replace(
            data,
            outcomes=(
                replace(
                    outcome, closing_wip_pieces=0, completed_good_pieces=data.orders[0].quantity + 1
                ),
                *data.outcomes[1:],
            ),
        )
    elif kind == "zero_capacity_production":
        data = replace(data, plans=(replace(plan, machine_available=False), *data.plans[1:]))
    elif kind == "physical_envelope":
        data = replace(data, outcomes=(replace(outcome, realized_workers=0), *data.outcomes[1:]))
    elif kind == "wrong_partition":
        data = replace(
            data, membership=(replace(data.membership[0], partition="test"), *data.membership[1:])
        )
    elif kind == "wrong_population":
        data = replace(
            data,
            membership=(
                replace(data.membership[0], population="unseen_factory"),
                *data.membership[1:],
            ),
        )
    elif kind == "wrong_calendar":
        data = replace(
            data,
            shifts=(
                replace(data.shifts[0], end=data.shifts[0].end + timedelta(hours=1)),
                *data.shifts[1:],
            ),
        )
    elif kind == "duplicate_crew_slot":
        second = data.plans[1]
        data = replace(data, plans=(plan, replace(second, crew_id=plan.crew_id), *data.plans[2:]))
    elif kind == "loss_exceeds_minutes":
        data = replace(
            data, outcomes=(replace(outcome, unplanned_loss_minutes=999), *data.outcomes[1:])
        )
    elif kind == "bool_count":
        data = replace(data, plans=(replace(plan, planned_workers=True), *data.plans[1:]))
    with pytest.raises(ValueError):
        validate_dataset(data, synthetic_config)


def test_absent_embargo_is_rejected_when_cross_factory_labels_mature_too_late(synthetic_config):
    config = replace(synthetic_config, embargo_dates=0)
    with pytest.raises(ValueError, match="LABEL_AVAILABILITY_REQUIRES_LONGER_EMBARGO"):
        validate_dataset(generate(config), config)
