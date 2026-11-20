"""Hand-calculated capacity, rounded duration, deltas and same-demand comparison."""

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

import loometric.scenarios.engine as engine
from loometric.scenarios.application import AppliedScenario
from loometric.scenarios.loading import load_specification
from loometric.scenarios.metrics import compare_objectives, scalar_delta
from loometric.scheduling.dispatcher import dispatch
from loometric.scheduling.loading import load_instance
from loometric.scheduling.metrics import calculate_metrics
from loometric.scheduling.verification import verify_schedule

EXAMPLES = Path(__file__).resolve().parents[2] / "examples/scenarios"


@pytest.mark.parametrize(
    "name,finished,available,makespan",
    [
        ("additional-workers", 55, "67.5", 59),
        ("reduced-efficiency", 10, "22.5", 20),
        ("added-shift", 55, "105", 70),
        ("downtime-reduction", 55, "55", 60),
        ("downtime-removal", 55, "60", 55),
        ("downtime-addition", 30, "40", 55),
        ("unavailable-line", 0, "0", None),
        ("removed-shift", 0, "0", None),
        ("multiple-changes", 55, "135", 26),
        ("no-improvement", 45, "50", 60),
    ],
)
def test_independent_hand_calculations(capacity_baseline, name, finished, available, makespan):
    report = engine.compare_scenario(
        capacity_baseline, load_specification(EXAMPLES / f"{name}.json")
    )
    before, after = (report[key]["evaluation"]["metrics"] for key in ("baseline", "scenario"))
    assert before["scheduled_units"] == 45 and before["unscheduled_units"] == 10
    assert before["available_standard_minutes"] == "45" and before["makespan_minutes"] == 60
    assert after["scheduled_units"] == finished and after["unscheduled_units"] == 55 - finished
    assert (
        after["available_standard_minutes"] == available and after["makespan_minutes"] == makespan
    )
    assert (
        report["same_demand_verified"]
        and report["baseline"]["evaluation"]["verification"]["feasible"]
    )
    assert report["scenario"]["evaluation"]["verification"]["feasible"]


def test_extra_workers_change_capacity_and_utilization_denominator(capacity_baseline, workers_spec):
    report = engine.compare_scenario(capacity_baseline, workers_spec)
    delta = report["metric_deltas"]
    assert delta["scheduled_units"]["absolute_change"] == 10
    assert Decimal(delta["available_standard_minutes"]["percentage_change"]) == 50
    assert delta["available_line_minutes"]["absolute_change"] == "0"
    assert Decimal(delta["line_utilization"]["absolute_change"]) < 0
    assert delta["line_utilization"]["percentage_point_change"] is not None
    assert report["interpretation"]["standard_capacity_increased"]
    assert report["interpretation"]["unfinished_demand_reduced"]
    assert not report["interpretation"]["causal_productivity_estimate"]


def test_capacity_increase_can_have_no_objective_benefit(capacity_baseline):
    report = engine.compare_scenario(
        capacity_baseline, load_specification(EXAMPLES / "no-improvement.json")
    )
    assert report["selected_comparison"]["relation"] == "TIE"
    assert report["metric_deltas"]["available_standard_minutes"]["absolute_change"] == "5"
    assert report["metric_deltas"]["unused_standard_minutes"]["absolute_change"] == "5"


def test_greedy_can_worsen_finished_goods_despite_more_capacity():
    report = engine.compare_scenario(
        load_instance(EXAMPLES / "routing-baseline.json"),
        load_specification(EXAMPLES / "capacity-greedy-regression.json"),
    )
    assert report["baseline"]["evaluation"]["metrics"]["scheduled_units"] == 28
    assert report["scenario"]["evaluation"]["metrics"]["scheduled_units"] == 18
    assert report["selected_comparison"]["relation"] == "WORSE"
    assert report["selected_comparison"]["deciding_objective"] == "unfinished_units"
    assert report["metric_deltas"]["makespan_minutes"]["absolute_change"] == -1
    assert report["interpretation"]["standard_capacity_increased"]


@pytest.mark.parametrize(
    "before,after,unit,status,absolute,points",
    [
        (0, 0, "piece", "BASELINE_ZERO", 0, None),
        (0, 10, "piece", "BASELINE_ZERO", 10, None),
        (None, 10, "minute", "NULL_VALUE", None, None),
        (5, None, "minute", "NULL_VALUE", None, None),
        (Decimal("0.5"), Decimal("0.25"), "ratio", "DEFINED", Decimal("-0.25"), Decimal("-25")),
    ],
)
def test_null_zero_and_percentage_points(before, after, unit, status, absolute, points):
    result = scalar_delta(before, after, unit)
    assert result.percentage_status == status and result.absolute_change == absolute
    assert result.percentage_point_change == points
    if status != "DEFINED":
        assert result.percentage_change is None
    else:
        assert result.percentage_change == -50


def test_empty_plans_keep_null_metrics_and_zero_objective(capacity_baseline, workers_spec):
    old = capacity_baseline.planning
    baseline = replace(
        capacity_baseline, planning=replace(old, lines=(replace(old.lines[0], worker_count=0),))
    )
    spec = replace(workers_spec, baseline_fingerprint=engine.instance_fingerprint(baseline))
    report = engine.compare_scenario(baseline, spec)
    assert report["baseline"]["evaluation"]["metrics"]["makespan_minutes"] is None
    assert report["metric_deltas"]["makespan_minutes"]["percentage_status"] == "NULL_VALUE"
    assert (
        report["metric_deltas"]["available_standard_minutes"]["percentage_status"]
        == "BASELINE_ZERO"
    )
    assert report["selected_comparison"]["baseline_objectives"]["makespan_minutes"] == 0


def test_same_demand_guard_rejects_corrupt_transform(capacity_baseline, workers_spec, monkeypatch):
    old = capacity_baseline.planning
    drift = replace(
        capacity_baseline,
        planning=replace(old, orders=(replace(old.orders[0], quantity=99), *old.orders[1:])),
    )
    monkeypatch.setattr(engine, "apply_scenario", lambda *args: AppliedScenario(drift, ()))
    with pytest.raises(ValueError, match="identical order demand"):
        engine.compare_scenario(capacity_baseline, workers_spec)


def test_reference_verifier_is_a_hard_gate(capacity_baseline, workers_spec, monkeypatch):
    import loometric.scenarios.selection as selection

    proposal = dispatch(capacity_baseline)
    bad = replace(proposal.allocations[0], quantity=999)
    monkeypatch.setattr(selection, "dispatch", lambda *args: replace(proposal, allocations=(bad,)))
    with pytest.raises(ValueError, match="failed independent verification"):
        engine.compare_scenario(capacity_baseline, workers_spec)


def test_objective_comparison_matches_existing_m03b_definition(capacity_baseline):
    from loometric.optimization.comparison import compare_quality

    baseline = calculate_metrics(capacity_baseline, dispatch(capacity_baseline))
    better = replace(baseline, unscheduled_units=0, priority_weighted_tardiness_minutes=999)
    assert (
        compare_objectives(baseline, better)["relation"]
        == compare_quality(better, baseline).relation
        == "BETTER"
    )


def test_multistage_precedence_is_preserved(workers_spec):
    baseline = load_instance(EXAMPLES.parent / "scheduling/parallel-routing.json")
    line = baseline.planning.lines[0]
    from loometric.scenarios.application import apply_scenario
    from loometric.scenarios.contracts import SetWorkers

    spec = replace(
        workers_spec,
        baseline_instance_id=baseline.instance_id,
        baseline_fingerprint=engine.instance_fingerprint(baseline),
        changes=(SetWorkers(line.line_id, line.worker_count + 1),),
    )
    scenario = apply_scenario(baseline, spec).instance
    proposal = dispatch(scenario)
    assert verify_schedule(scenario, proposal).feasible
    allocated = {item.key: item for item in proposal.allocations}
    for order in scenario.planning.orders:
        for previous, current in zip(
            order.required_stages[:-1], order.required_stages[1:], strict=True
        ):
            if (order.order_id, current) in allocated:
                assert (
                    allocated[order.order_id, previous].interval.end
                    <= allocated[order.order_id, current].interval.start
                )
