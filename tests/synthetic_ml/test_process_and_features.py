import random
import subprocess
import sys
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal, localcontext
from pathlib import Path

import pytest

from loometric.synthetic_ml.audit import quality_report
from loometric.synthetic_ml.contracts import target_value
from loometric.synthetic_ml.features import (
    FEATURE_COLUMNS,
    References,
    available_minutes,
    build_features,
    training_examples,
)
from loometric.synthetic_ml.generation import generate
from loometric.synthetic_ml.splitting import TEST_POPULATIONS
from loometric.synthetic_ml.validation import validate_dataset


def test_repeatability_local_rng_and_decimal_context(synthetic_data, synthetic_config):
    random.seed(731)
    state = random.getstate()
    expected = training_examples(synthetic_data)
    with localcontext() as context:
        context.prec = 3
        again = generate(synthetic_config)
        assert again == synthetic_data
        assert training_examples(again) == expected
    assert random.getstate() == state


@pytest.mark.parametrize("seed", [19, 42, 73])
@pytest.mark.parametrize("scenario", ["baseline", "disruption", "workload_surge"])
def test_seed_scenario_properties(synthetic_config, seed, scenario):
    config = replace(synthetic_config, seed=seed, scenario=scenario, calendar_days=35)
    data = generate(config)
    validate_dataset(data, config)
    assert {line.stage.value for line in data.lines} == {
        "cutting",
        "sewing",
        "finishing",
        "quality_control",
        "packing",
    }
    assert {m.population for m in data.membership if m.partition == "test"} == set(TEST_POPULATIONS)
    assert len({p.observation_id for p in data.plans}) == len(data.plans)


@pytest.mark.parametrize(
    "group,axis",
    [
        ("unseen_crew", "crew_id"),
        ("unseen_line", "line_id"),
        ("unseen_factory", "factory_id"),
        ("unseen_style", "style_id"),
        ("future_familiar", None),
    ],
)
def test_separate_generalization_populations(synthetic_data, group, axis):
    rows = {r["observation_id"]: r for r in build_features(synthetic_data)}
    training = [
        rows[m.observation_id]["context"]
        for m in synthetic_data.membership
        if m.partition == "train"
    ]
    tests = [
        rows[m.observation_id]["context"]
        for m in synthetic_data.membership
        if m.population == group
    ]
    assert tests
    if axis:
        assert not {r[axis] for r in training} & {r[axis] for r in tests}
    else:
        for key in training[0]:
            assert {r[key] for r in tests} <= {r[key] for r in training}


def test_night_shifts_label_maturity_and_purged_boundaries(synthetic_data):
    refs = References.from_dataset(synthetic_data)
    outcomes = {o.observation_id: o for o in synthetic_data.outcomes}
    plans = {p.observation_id: p for p in synthetic_data.plans}
    assert all(s.end.date() > s.start.date() for s in synthetic_data.shifts if s.kind == "night")
    members = synthetic_data.membership
    for before, after in (("train", "validation"), ("validation", "test")):
        assert max(
            outcomes[m.observation_id].available_at for m in members if m.partition == before
        ) < min(plans[m.observation_id].cutoff for m in members if m.partition == after)
    by_date = {}
    for m in members:
        day = refs.shifts[plans[m.observation_id].shift_id].start.date()
        by_date.setdefault(day, set()).add(m.partition)
    assert all(len(parts) == 1 for parts in by_date.values())
    assert sum(parts == {"gap"} for parts in by_date.values()) == 2


def test_features_cannot_access_any_outcome_or_membership(synthetic_data):
    class Prohibited:
        def __iter__(self):
            raise AssertionError("A feature builder must not read outcomes or split membership")

    altered = replace(synthetic_data, outcomes=Prohibited(), membership=Prohibited())
    rows = build_features(altered)
    assert rows == build_features(synthetic_data)
    assert all(tuple(row["inputs"]) == FEATURE_COLUMNS for row in rows)
    assert all(set(row) == {"observation_id", "cutoff", "context", "inputs"} for row in rows)


def test_train_only_join_ignores_all_heldout_outcomes(synthetic_data):
    class UnavailableOutcome:
        def __init__(self, identifier):
            self.observation_id = identifier

        def __getattr__(self, name):
            raise AssertionError("Held-out label access is forbidden")

    train = {m.observation_id for m in synthetic_data.membership if m.partition == "train"}
    changed = replace(
        synthetic_data,
        outcomes=tuple(
            o if o.observation_id in train else UnavailableOutcome(o.observation_id)
            for o in synthetic_data.outcomes
        ),
    )
    expected = training_examples(synthetic_data)
    assert training_examples(changed) == expected
    assert {row["observation_id"] for row in expected} == train
    assert any(
        row["label"]["status"] == "ZERO_PLANNED_CAPACITY"
        and row["label"]["standard_capacity_attainment"] is None
        for row in expected
    )


def test_hidden_noise_changes_labels_with_identical_exposed_features(synthetic_config):
    quiet = generate(replace(synthetic_config, process_noise_bps=0))
    noisy = generate(replace(synthetic_config, process_noise_bps=4000))
    assert quiet.plans == noisy.plans and build_features(quiet) == build_features(noisy)
    assert quiet.outcomes != noisy.outcomes
    assert [o.completed_good_pieces for o in quiet.outcomes] != [
        o.completed_good_pieces for o in noisy.outcomes
    ]


def test_distribution_shift_does_not_change_training(synthetic_data, synthetic_config):
    train = {m.observation_id for m in synthetic_data.membership if m.partition == "train"}
    disrupted = generate(replace(synthetic_config, scenario="disruption"))
    surge = generate(replace(synthetic_config, scenario="workload_surge"))
    assert disrupted.plans == synthetic_data.plans
    assert [o for o in disrupted.outcomes if o.observation_id in train] == [
        o for o in synthetic_data.outcomes if o.observation_id in train
    ]
    assert [p for p in surge.plans if p.observation_id in train] == [
        p for p in synthetic_data.plans if p.observation_id in train
    ]
    assert sum(o.completed_good_pieces for o in disrupted.outcomes) < sum(
        o.completed_good_pieces for o in synthetic_data.outcomes
    )
    assert sum(o.quantity for o in surge.orders) > sum(o.quantity for o in synthetic_data.orders)


def test_overlapping_planned_stops_are_unioned_and_no_incomplete_piece_credit(synthetic_data):
    plan = synthetic_data.plans[0]
    shift = References.from_dataset(synthetic_data).shifts[plan.shift_id]
    changed = replace(
        plan,
        machine_available=True,
        downtime_start=shift.break_start,
        downtime_end=shift.break_end + timedelta(minutes=15),
    )
    assert available_minutes(changed, shift) == 435
    result = target_value(3, Decimal("2.75"), 100)
    assert result == ("VALID", Decimal("0.0825"))


def test_quality_is_descriptive_and_test_targets_not_summarized(synthetic_data, synthetic_config):
    report = quality_report(synthetic_data, synthetic_config)
    assert report["status"] == "VALID"
    assert report["quality_score"] is None
    assert report["reserved_test_target_statistics"] == "NOT_COMPUTED"
    assert set(report["development_target_statistics"]) == {"train", "validation"}
    assert report["model_training_performed"] is report["planning_conversion_authorized"] is False
    assert (
        report["test_population_entity_coverage"]["unseen_factory"]["crew_id"]["unseen_vs_train"]
        > 0
    )
    assert report["development_target_statistics"]["train"]["above_one"] > 0


def test_generation_imports_no_ml_and_reads_no_historical_data():
    root = Path(__file__).resolve().parents[2]
    code = """
import sys
sys.path.insert(0, 'src')
def deny_file(event, args):
    if event == 'open' and isinstance(args[0], str):
        path = args[0].replace(chr(92), '/').lower()
        if 'data/raw/' in path or 'data/processed/' in path:
            raise AssertionError('Historical/protected data read')
sys.addaudithook(deny_file)
from loometric.synthetic_ml.generation import generate
from loometric.synthetic_ml.configuration import GenerationConfig
from loometric.synthetic_ml.validation import validate_dataset
d = generate(GenerationConfig(calendar_days=35))
validate_dataset(d, GenerationConfig(calendar_days=35))
for module in sys.modules:
    assert module.split('.')[0] not in {'sklearn','pandas','numpy','joblib','ortools'}
"""
    subprocess.run([sys.executable, "-S", "-c", code], cwd=root, check=True, capture_output=True)
