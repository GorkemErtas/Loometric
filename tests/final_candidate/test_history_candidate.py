"""Mechanical fixtures only; no actual EXP-010 outcomes or model fitting."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from threadpoolctl import threadpool_limits

from loometric.final_candidate import data, study
from loometric.final_candidate.history import MatureObservation, history_snapshot
from loometric.final_candidate.model import HistoryBoost
from loometric.prospective_evaluation.storage import decode_rows
from loometric.synthetic_ml.configuration import GenerationConfig
from loometric.synthetic_ml.generation import generate


class Foundation:
    def predict(self, X):
        return np.full(len(X), 0.8)

    def fit(self, *args):
        raise AssertionError("Frozen foundation must never fit")


def test_history_excludes_current_future_other_crew_and_line_and_handles_censoring():
    cutoff = datetime(2034, 3, 1, 7, 30, tzinfo=UTC)
    start = cutoff + timedelta(minutes=30)
    past = MatureObservation(
        "past", "crew", "line", start - timedelta(days=1), cutoff - timedelta(hours=10), 0.9, False
    )
    records = [
        past,
        replace(past, observation_id="past2", attainment=0.7),
        replace(
            past, observation_id="future", available_at=cutoff + timedelta(seconds=1), attainment=99
        ),
        replace(past, observation_id="current", attainment=99),
        replace(past, observation_id="othercrew", crew_id="other", attainment=99),
        replace(past, observation_id="otherline", line_id="other", attainment=99),
        replace(past, observation_id="censored", attainment=99, censored=True),
    ]
    result = history_snapshot(
        records,
        crew_id="crew",
        line_id="line",
        observation_id="current",
        shift_start=start,
        cutoff=cutoff,
    )
    assert result["recent_attainment_mean"] == 0.8
    assert result["recent_attainment_std"] == pytest.approx(0.1)
    assert result["history_count"] == 3 and result["uncensored_history_count"] == 2
    assert result["history_age_hours"] == 10
    assert set(result["source_observation_ids"]) == {"past", "past2", "censored"}


def test_current_and_future_label_mutations_cannot_change_earlier_features():
    parameters = GenerationConfig(seed=99171, calendar_days=35, factories=2, styles=3)
    original = generate(parameters)
    before = data.project(original, parameters, True)
    plan = original.plans[150]
    changed = replace(
        original,
        outcomes=tuple(
            replace(
                o,
                completed_good_pieces=0,
                closing_wip_pieces=next(
                    p for p in original.plans if p.observation_id == o.observation_id
                ).opening_wip_pieces
                + next(
                    p for p in original.plans if p.observation_id == o.observation_id
                ).planned_release_pieces,
            )
            if o.observation_id == plan.observation_id
            else o
            for o in original.outcomes
        ),
    )
    after = data.project(changed, parameters, True)

    def earlier(buffers):
        return [
            r
            for r in decode_rows("features.jsonl", buffers["features.jsonl"])
            if datetime.fromisoformat(r["cutoff"]) <= plan.cutoff
        ]

    assert earlier(before) == earlier(after)


def test_single_residual_fit_leaves_foundation_untouched_and_respects_offered_work():
    parameters = GenerationConfig(seed=99171, calendar_days=35, factories=2, styles=3)
    projected = data.project(generate(parameters), parameters, True)
    rows = [
        r for r in decode_rows("features.jsonl", projected["features.jsonl"]) if r["defined_target"]
    ][:60]
    X = study.frame(rows)
    y = pd.Series(np.linspace(0.3, 1.2, len(rows)))
    options = {**data.config()["estimator"], "max_iter": 4, "min_samples_leaf": 5}
    model = HistoryBoost(Foundation(), options)
    with threadpool_limits(limits=1):
        model.fit(X, y)
        predictions = model.predict(X)
    ceiling = (
        X.order_quantity
        * X.standard_worker_minutes_per_piece
        / (X.available_minutes * X.planned_workers)
    )
    assert (
        np.isfinite(predictions).all()
        and (predictions >= 0).all()
        and (predictions <= ceiling + 1e-12).all()
    )
    with pytest.raises(ValueError, match="SINGLE_ESTIMATOR_FIT_ONLY"):
        model.fit(X, y)


@pytest.mark.parametrize(
    "group,partition",
    [
        ("heldout", "fit"),
        ("heldout", "context"),
        ("development", "context"),
        ("development", "embargo"),
        ("heldout", "test"),
    ],
)
def test_reserved_partitions_fail_before_open(tmp_path, group, partition):
    with pytest.raises(ValueError, match="RESERVED_LABEL_ACCESS"):
        data.read_labels(tmp_path, group, "private", partition)


def test_no_public_serving_or_old_reserved_reuse_in_declaration():
    c = data.config()
    assert c["budget"]["estimator_fits"] == 1 and c["budget"]["hyperparameter_trials"] == 0
    assert (
        c["promotion_decision"] == "NO_ML_PROMOTION" and c["production_serving_authorized"] is False
    )
    assert not set(c["development_seeds"] + c["heldout_seeds"]) & {19, 42, 73, 101, 211, 307, 401}
    assert set(c["development_seeds"]).isdisjoint(c["heldout_seeds"])
