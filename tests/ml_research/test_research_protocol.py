import copy
import json
from datetime import timedelta

import pandas as pd
import pytest

from loometric.ml_research.features import DERIVED_UNITS, PlannedFeatures
from loometric.ml_research.protocol import load_protocol, research_folds
from loometric.ml_research.selection import choose_candidate
from loometric.synthetic_ml.features import FEATURE_COLUMNS


def test_planned_features_have_exact_units_and_no_leakage(research_population):
    X = research_population.X
    before = X.copy(deep=True)
    features = PlannedFeatures().fit_transform(X)
    row, original = features.iloc[0], X.iloc[0]
    assert tuple(features.columns) == (*FEATURE_COLUMNS, *DERIVED_UNITS)
    assert row.planned_worker_minutes == 1680
    assert row.planned_load_ratio == pytest.approx(600 * 2.5 / 1680)
    assert row.one_piece_attainment_quantum == pytest.approx(2.5 / 1680)
    assert row.opening_wip_share == pytest.approx(100 / 600)
    assert row.planned_downtime_fraction == 30 / 480
    assert row[f"load_at_{original.stage}"] == row.planned_load_ratio
    pd.testing.assert_frame_equal(X, before)
    pd.testing.assert_frame_equal(features, PlannedFeatures().fit_transform(X))
    assert DERIVED_UNITS["planned_worker_minutes"] == "worker_minute"
    for field in ("actual", "demand_censored", "seed", "factory_id", "scenario"):
        with pytest.raises(ValueError):
            PlannedFeatures().fit_transform(X.assign(**{field: 1}))


@pytest.mark.parametrize("kind", ["zero_capacity", "invalid_stock", "reordered", "missing"])
def test_invalid_feature_contract_is_not_imputed(research_population, kind):
    X = research_population.X.copy()
    if kind == "zero_capacity":
        X.loc[X.index[0], "planned_workers"] = 0
    elif kind == "invalid_stock":
        X.loc[X.index[0], "order_quantity"] += 1
    elif kind == "reordered":
        X = X.loc[:, list(reversed(FEATURE_COLUMNS))]
    else:
        X = X.drop(columns="planned_workers")
    with pytest.raises(ValueError):
        PlannedFeatures().fit_transform(X)


def test_new_windows_use_training_only_and_purge_dates(research_population):
    folds = research_folds(research_population)
    assert [len(f.evaluation_dates) for f in folds] == [6, 6, 6]
    assert [len(f.train_dates) for f in folds] == [11, 17, 23]
    seen = set()
    for fold in folds:
        assert not set(fold.train_ids) & set(fold.evaluation_ids)
        assert not seen & set(fold.evaluation_ids)
        seen.update(fold.evaluation_ids)
        assert max(
            research_population.metadata.loc[list(fold.train_ids), "label_available_at"]
        ) < min(research_population.metadata.loc[list(fold.evaluation_ids), "cutoff"])
    assert research_folds(research_population) == folds


def test_immature_training_labels_fail_closed(research_population):
    research_population.metadata.loc[research_population.X.index[0], "label_available_at"] += (
        timedelta(days=100)
    )
    with pytest.raises(ValueError, match="MATURITY"):
        research_folds(research_population)


def test_protocol_is_closed_and_predeclared(tmp_path):
    config = load_protocol()
    assert len(config["candidates"]) == 6 and config["model_seed"] == 42
    for key, value in (("model_seed", 43), ("references", ["forest-12"]), ("extra", True)):
        path = tmp_path / "changed.json"
        path.write_text(json.dumps({**config, key: value}))
        with pytest.raises(ValueError, match="FROZEN"):
            load_protocol(path)


def selection_evidence(config):
    names = ["grouped_mean", "forest-12", "hist-31", *(c["name"] for c in config["candidates"])]
    evaluations, temporal = {}, {}
    for case in (
        "development-19-baseline",
        "development-42-baseline",
        "development-73-baseline",
        "benchmark-42-baseline",
    ):
        evaluations[case], temporal[case] = {}, {}
        for name in names:
            value = (
                0.2
                if name == "grouped_mean"
                else 0.15
                if name in ("forest-12", "hist-31")
                else 0.12
            )
            metrics = {"mae": value, "p95_positive_error": value, "worst_absolute_error": value}
            evaluations[case][name] = {
                "overall": metrics,
                "slices": {"stage": {"packing": metrics.copy()}},
            }
            temporal[case][name] = [{"mae": value} for _ in range(3)]
    return evaluations, temporal


def test_selection_uses_only_training_evidence_and_stable_preference():
    config = load_protocol()
    evaluations, temporal = selection_evidence(config)
    names = [c["name"] for c in config["candidates"]]
    result = choose_candidate(evaluations, temporal, names, config["selection"])
    assert result["status"] == "RESEARCH_CANDIDATE"
    assert result["selected_candidate"] == config["selection"]["preference"][0]
    assert result["promotion_decision"] == "NO_ML_PROMOTION"
    assert result["validation_used_for_selection"] is False
    assert result == choose_candidate(
        copy.deepcopy(evaluations), temporal, names, config["selection"]
    )


@pytest.mark.parametrize("failure", ["stage", "tail", "world", "temporal", "no_gain"])
def test_best_average_does_not_override_research_guards(failure):
    config = load_protocol()
    evaluations, temporal = selection_evidence(config)
    names = [c["name"] for c in config["candidates"]]
    for models in evaluations.values():
        for name in names:
            if failure == "stage":
                models[name]["slices"]["stage"]["packing"]["mae"] = 0.3
            if failure == "tail":
                models[name]["overall"]["worst_absolute_error"] = 0.3
            if failure in ("no_gain", "world"):
                models[name]["overall"]["mae"] = 0.3
    if failure == "temporal":
        for models in temporal.values():
            for name in names:
                models[name] = [{"mae": 0.3} for _ in range(3)]
    result = choose_candidate(evaluations, temporal, names, config["selection"])
    assert result["status"] == "NO_RESEARCH_CANDIDATE"
    assert result["selected_candidate"] is None
