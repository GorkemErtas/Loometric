from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from threadpoolctl import threadpool_limits

from loometric.synthetic_ml.features import FEATURE_COLUMNS
from loometric.synthetic_training.configuration import load_study
from loometric.synthetic_training.data import Population
from loometric.synthetic_training.folds import expanding_folds
from loometric.synthetic_training.metrics import analyze, error_summary
from loometric.synthetic_training.models import (
    MeanModel,
    build_model,
    model_metadata,
    workload_band,
)
from loometric.synthetic_training.risk import (
    assess_support,
    band_diagnostics,
    residual_reference,
    support_profile,
)


@pytest.fixture(scope="module")
def toy():
    # Private deterministic unit records, not experiment evidence.
    dates = [
        (datetime(2030, 1, 7, tzinfo=timezone(timedelta(hours=3))) + timedelta(days=i)).date()
        for i in range(35)
    ]
    dates = [d for d in dates if d.weekday() != 6]
    rows, meta = [], []
    for i in range(len(dates) * 8):
        day = dates[i // 8]
        rows.append(
            {
                "stage": ("cutting", "sewing", "finishing", "quality_control", "packing")[i % 5],
                "shift_kind": "night" if i % 2 else "day",
                "weekday": str(day.weekday()),
                "planned_workers": float(4 + i % 4),
                "skill_level": float(1 + i % 5),
                "style_complexity": float(1 + i % 5),
                "standard_worker_minutes_per_piece": 2.5,
                "planned_machine_available": 1.0,
                "available_minutes": 420.0,
                "planned_downtime_minutes": 30.0,
                "opening_wip_pieces": 20.0,
                "planned_release_pieces": float(80 + i % 17),
                "order_quantity": float(100 + i % 17),
            }
        )
        start = datetime.combine(day, datetime.min.time(), tzinfo=timezone(timedelta(hours=3)))
        meta.append(
            {
                "start_date": day,
                "cutoff": start + timedelta(hours=7, minutes=30),
                "label_available_at": start + timedelta(hours=18),
                "stage": rows[-1]["stage"],
                "shift_kind": rows[-1]["shift_kind"],
                "staffing_band": "1-5",
                "workload_band": "low",
                "interruption_band": "1-30",
                "low_demand": True,
                "demand_censored": False,
            }
        )
    index = pd.Index([f"toy-{i}" for i in range(len(rows))])
    return Population(
        pd.DataFrame(rows, index=index, columns=FEATURE_COLUMNS),
        pd.Series([0.4 + (i % 11) * 0.06 for i in range(len(rows))], index=index),
        pd.DataFrame(meta, index=index),
        (),
        "a" * 64,
    )


@pytest.mark.parametrize(
    "name",
    [
        "global_mean",
        "stage_mean",
        "grouped_mean",
        "ridge-1",
        "ridge-10",
        "forest-6",
        "forest-12",
        "hist-15",
        "hist-31",
    ],
)
def test_reproducible_training_preprocessing_and_unknown_category(toy, name):
    config = load_study(Path(__file__).resolve().parents[2] / "configs/synthetic_training_v1.json")
    spec = next((s for s in config["search"] if s["name"] == name), {"name": name})
    with threadpool_limits(limits=1):
        first = build_model(spec, 42).fit(toy.X, toy.y)
        second = build_model(spec, 42).fit(toy.X, toy.y)
        np.testing.assert_array_equal(first.predict(toy.X), second.predict(toy.X))
        unknown = toy.X.iloc[:1].copy()
        unknown.loc[:, "stage"] = "unseen-stage"
        assert np.isfinite(first.predict(unknown)).all()
    profile = support_profile(toy.X, toy.y)
    assert assess_support(unknown.iloc[0].to_dict(), profile)["status"] == "ABSTAIN"
    metadata = model_metadata(first)
    if name.startswith("ridge"):
        np.testing.assert_allclose(metadata["numeric_training_mean"], toy.X.iloc[:, 3:].mean())
    with pytest.raises(ValueError):
        first.predict(toy.X.assign(actual_productivity=toy.y))
    with pytest.raises(ValueError):
        first.predict(toy.X.loc[:, list(reversed(FEATURE_COLUMNS))])


def test_unknown_mean_groups_fall_back_to_global_and_no_clamping(toy):
    y = toy.y * 0 + 1.4
    model = MeanModel("grouped_mean").fit(toy.X, y)
    unknown = toy.X.iloc[:2].copy()
    unknown.loc[:, "stage"] = "unseen"
    assert list(model.predict(unknown)) == [1.4, 1.4]


def test_planned_workload_boundary_uses_exact_declared_decimal_units():
    row = {
        "order_quantity": 100.0,
        "standard_worker_minutes_per_piece": 4.86,
        "available_minutes": 405.0,
        "planned_workers": 2.0,
    }
    assert row["order_quantity"] * row["standard_worker_minutes_per_piece"] / 810 > 0.6
    assert workload_band(row) == "low"  # 100 × 4.86 / (405 × 2) = exactly 0.6.
    assert workload_band({**row, "standard_worker_minutes_per_piece": 4.87}) == "nominal"


def test_training_fold_dates_are_disjoint_purged_and_mature(toy):
    folds = expanding_folds(toy)
    observed = set()
    for fold in folds:
        assert not set(fold.evaluation_ids) & observed
        assert set(fold.train_ids) <= set(toy.X.index)
        assert max(toy.metadata.loc[list(fold.train_ids), "label_available_at"]) < min(
            toy.metadata.loc[list(fold.evaluation_ids), "cutoff"]
        )
        assert fold.train_dates[-1] < fold.evaluation_dates[0]
        observed.update(fold.evaluation_ids)


def test_hand_calculated_metrics_and_risk_band_do_not_claim_calibration():
    actual = pd.Series([0.0, 1.0, 2.0])
    prediction = pd.Series([1.0, 1.0, 4.0])
    result = error_summary(actual, prediction)
    assert result["mae"] == 1 and result["bias"] == 1
    assert result["rmse"] == pytest.approx(np.sqrt(5 / 3))
    assert result["median_absolute_error"] == 1
    assert result["p90_absolute_error"] == pytest.approx(1.8)
    assert result["p95_absolute_error"] == pytest.approx(1.9)
    assert result["worst_absolute_error"] == 2
    assert result["predictions_above_one"] == 1
    reference = residual_reference(
        [
            {"stage": "sewing", "prediction": p, "actual": a}
            for p, a in zip(prediction, actual, strict=True)
        ]
    )
    assert reference["coverage_guarantee"] is False
    assert reference["stage_radii"]["sewing"]["fallback_to_global"] is True
    bands = band_diagnostics(actual, prediction, pd.DataFrame({"stage": ["sewing"] * 3}), reference)
    assert bands["samples"] == 3 and bands["covered"] == 2
    assert bands["interval_endpoints_clipped"] is False


@pytest.mark.parametrize(
    "kind",
    [
        "zero",
        "unknown",
        "nonfinite",
        "negative_prediction",
        "over_one",
        "out_of_range",
        "missing",
        "future_label",
        "inconsistent_stock",
    ],
)
def test_unsupported_contexts_and_ranges_remain_explicit(toy, kind):
    profile = support_profile(toy.X, toy.y)
    inputs = toy.X.iloc[0].to_dict()
    prediction = 0.7
    expected = "ABSTAIN"
    if kind == "zero":
        inputs["available_minutes"] = 0
    elif kind == "unknown":
        inputs["shift_kind"] = "third-shift"
    elif kind == "nonfinite":
        inputs["standard_worker_minutes_per_piece"] = float("nan")
    elif kind == "negative_prediction":
        prediction = -0.1
    elif kind == "over_one":
        prediction, expected = 1.2, "REVIEW_REQUIRED"
    elif kind == "out_of_range":
        inputs["standard_worker_minutes_per_piece"], expected = 15.0, "REVIEW_REQUIRED"
    elif kind == "missing":
        inputs.pop("skill_level")
    elif kind == "future_label":
        inputs["realized_workers"] = 5
    else:
        inputs["opening_wip_pieces"] = 999
    assert assess_support(inputs, profile, prediction)["status"] == expected


def test_all_error_slices_keep_identical_primary_observations(toy):
    result = analyze(toy.y, toy.y + 0.1, toy.metadata)
    for summaries in result["slices"].values():
        assert sum(s["samples"] for s in summaries.values()) == len(toy.y)
    assert result["overall"]["samples"] == len(toy.y)
