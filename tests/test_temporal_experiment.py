import json
from dataclasses import asdict, replace
from pathlib import Path
from statistics import fmean, pstdev
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.pipeline import Pipeline

import loometric.experiments.temporal as temporal
from loometric.data.loading import clean_data
from loometric.data.profiling import fingerprint
from loometric.data.schema import TARGET
from loometric.data.splitting import apply_split_config, make_split_config, save_split_config
from loometric.data.temporal import make_expanding_folds
from loometric.evaluation import RegressionMetrics
from loometric.features import SOURCE_COLUMNS

DIGEST = "a" * 64


@pytest.fixture
def temporal_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    """59 synthetic dates yield 35 original training dates, independent of real findings."""
    records = []
    for number, date in enumerate(pd.date_range("2015-01-01", periods=59)):
        for department in range(2):
            record = raw_data.iloc[department].copy()
            record["date"], record["day"] = date.strftime("%m/%d/%Y"), date.day_name()
            record[TARGET] = str(0.4 + number * 0.003 + department * 0.1)
            records.append(record)
    return clean_data(pd.DataFrame(records, dtype="string").reset_index(drop=True))


def test_audit_uses_exact_fixed_models_and_frozen_forest() -> None:
    assert temporal.MODEL_NAMES == (
        "global_mean",
        "department_mean",
        "linear_A",
        "linear_B",
        "forest_B_RF-01",
    )
    assert asdict(temporal.FROZEN_FOREST) == {
        "name": "RF-01",
        "n_estimators": 100,
        "max_depth": 3,
        "min_samples_leaf": 20,
    }
    assert temporal.FROZEN_FEATURES == {
        "A": ("department", "team"),
        "B": ("department", "team", "day_of_week", "day_of_month"),
    }


def test_each_fold_fits_fresh_preprocessing_on_prefix_and_never_touches_outer_holdouts(
    temporal_data: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = make_split_config(temporal_data, DIGEST)
    splits = apply_split_config(temporal_data, config, dataset_sha256=DIGEST)
    # Deliberately no .validation or .test attributes, even during diagnostics.
    monkeypatch.setattr(
        temporal, "apply_split_config", lambda *args, **kwargs: SimpleNamespace(train=splits.train)
    )
    folds = make_expanding_folds(splits.train, config.train)
    train_indices = [
        splits.train.index[splits.train["date"].between(fold.train.start, fold.train.end)]
        for fold in folds
    ]
    original_fit, original_predict = Pipeline.fit, Pipeline.predict
    original_features, original_metrics = temporal.build_features, temporal.regression_metrics
    fitted: list[Pipeline] = []
    built: list[int] = []

    def fit(self: Pipeline, features: pd.DataFrame, target: pd.Series) -> Pipeline:
        expected = train_indices[len(fitted) // 3]
        assert features.index.equals(expected)
        assert target.equals(splits.train.loc[expected, TARGET])
        assert all(self is not previous for previous in fitted)
        assert all(
            self.named_steps["preprocessing"] is not previous.named_steps["preprocessing"]
            for previous in fitted
        )
        fitted.append(self)
        return original_fit(self, features, target)

    def predict(self: Pipeline, features: pd.DataFrame) -> object:
        assert set(features.index).issubset(set(splits.train.index))
        return original_predict(self, features)

    def build(scheduled: pd.DataFrame) -> pd.DataFrame:
        assert set(scheduled.columns) == set(SOURCE_COLUMNS)
        assert set(scheduled.index).issubset(set(splits.train.index))
        built.append(len(scheduled))
        return original_features(scheduled)

    def score(actual: pd.Series, predicted: pd.Series) -> RegressionMetrics:
        assert set(actual.index).issubset(set(splits.train.index))
        return original_metrics(actual, predicted)

    monkeypatch.setattr(Pipeline, "fit", fit)
    monkeypatch.setattr(Pipeline, "predict", predict)
    monkeypatch.setattr(temporal, "build_features", build)
    monkeypatch.setattr(temporal, "regression_metrics", score)
    result = temporal.run_experiment(temporal_data, config, dataset_sha256=DIGEST)
    assert len(fitted) == 12
    assert built == [30, 10, 40, 10, 50, 10, 60, 10]
    assert len(result.out_of_fold.actuals) == len(set(result.out_of_fold.row_indices)) == 40


def test_evaluation_categories_and_labels_cannot_enter_an_earlier_fold_fit(
    temporal_data: pd.DataFrame,
) -> None:
    config = make_split_config(temporal_data, DIGEST)
    reference = temporal.run_experiment(temporal_data, config, dataset_sha256=DIGEST)
    changed = temporal_data.copy(deep=True)
    first = reference.folds[0].fold
    later = changed["date"].ge(first.evaluation.start)
    changed.loc[later, TARGET] = 4
    changed.loc[later, "team"] = 999
    actual = temporal.run_experiment(changed, config, dataset_sha256=DIGEST)
    for name in temporal.MODEL_NAMES:
        before, after = reference.folds[0].models[name], actual.folds[0].models[name]
        assert after.training_mae == before.training_mae
        assert after.estimator_parameters == before.estimator_parameters
        assert after.features.training_categories == before.features.training_categories
        if name.startswith("linear_") or name == temporal.FOREST_NAME:
            assert "999" not in after.features.training_categories["team"]
            assert after.features.unknown_validation_categories["team"] == 10
            # The next fold may legitimately learn this category from its earlier prefix.
            assert "999" in actual.folds[1].models[name].features.training_categories["team"]
    # Change labels alone: every first-fold prediction must remain exactly identical.
    changed["team"] = temporal_data["team"]
    label_only = temporal.run_experiment(changed, config, dataset_sha256=DIGEST)
    for name in temporal.MODEL_NAMES:
        assert (
            label_only.out_of_fold.predictions[name][:10]
            == reference.out_of_fold.predictions[name][:10]
        )


def test_outer_holdout_poisoning_and_excluded_fields_do_not_change_audit(
    temporal_data: pd.DataFrame,
) -> None:
    config = make_split_config(temporal_data, DIGEST)
    expected = temporal.run_experiment(temporal_data, config, dataset_sha256=DIGEST)
    changed = temporal_data.copy(deep=True)
    holdouts = changed["date"].gt(config.train.end)
    changed.loc[holdouts, TARGET] = float("nan")
    changed.loc[holdouts, "team"] = 999
    changed.loc[holdouts, "department"] = "outer-holdout-only"
    assert temporal.run_experiment(changed, config, dataset_sha256=DIGEST) == expected
    minimal = temporal_data.loc[:, (*SOURCE_COLUMNS, TARGET)]
    assert temporal.run_experiment(minimal, config, dataset_sha256=DIGEST) == expected


def test_reproducible_predictions_fold_metrics_and_forest_comparison_counts(
    temporal_data: pd.DataFrame,
) -> None:
    config = make_split_config(temporal_data, DIGEST)
    first = temporal.run_experiment(temporal_data, config, dataset_sha256=DIGEST)
    assert temporal.run_experiment(temporal_data, config, dataset_sha256=DIGEST) == first
    assert len(first.folds) == 4
    assert sum(asdict(first.forest_vs_department).values()) == 4
    for counts in first.forest_department_comparisons.values():
        assert sum(asdict(counts).values()) == 4
    for fold in first.folds:
        assert (
            fold.fold.train.end
            < fold.fold.evaluation.start
            <= fold.fold.evaluation.end
            <= config.train.end
        )
        for model in fold.models.values():
            assert model.evaluation_metrics.samples == 10
            assert model.training_seconds >= 0 and model.inference_seconds >= 0


def test_pooled_metrics_are_recomputed_from_disjoint_predictions_not_averaged_folds(
    temporal_data: pd.DataFrame,
) -> None:
    # Unequal row counts preserve dates, exercising row-weighted versus equal-fold summaries.
    data = pd.concat([temporal_data, temporal_data.iloc[[32, 32, 32]]], ignore_index=True)
    config = make_split_config(data, DIGEST)
    result = temporal.run_experiment(data, config, dataset_sha256=DIGEST)
    actuals = np.array(result.out_of_fold.actuals)
    for name, summary in result.pooled.items():
        predictions = np.array(result.out_of_fold.predictions[name])
        assert summary.metrics.mae == pytest.approx(mean_absolute_error(actuals, predictions))
        assert summary.metrics.rmse == pytest.approx(root_mean_squared_error(actuals, predictions))
        assert summary.metrics.r2 == pytest.approx(r2_score(actuals, predictions))
        assert summary.metrics.bias == pytest.approx(float((predictions - actuals).mean()))
        fold_errors = [fold.models[name].evaluation_metrics.mae for fold in result.folds]
        assert summary.mean_fold_mae == pytest.approx(fmean(fold_errors))
        assert summary.std_fold_mae == pytest.approx(pstdev(fold_errors))
        weighted_mae = sum(
            fold.models[name].evaluation_metrics.mae * fold.fold.evaluation.rows
            for fold in result.folds
        ) / len(actuals)
        assert summary.metrics.mae == pytest.approx(weighted_mae)
    assert result.pooled["global_mean"].metrics.mae != pytest.approx(
        result.pooled["global_mean"].mean_fold_mae
    )
    for department, scores in result.pooled[temporal.FOREST_NAME].department_metrics.items():
        indices = [
            i for i, value in enumerate(result.out_of_fold.departments) if value == department
        ]
        predicted = np.array(result.out_of_fold.predictions[temporal.FOREST_NAME])[indices]
        assert scores.mae == pytest.approx(mean_absolute_error(actuals[indices], predicted))


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ([-0.1, 0.1, 0.0, -1e-13], temporal.ComparisonCounts(1, 1, 2)),
        ([-0.1] * 4, temporal.ComparisonCounts(4, 0, 0)),
        ([0.1] * 4, temporal.ComparisonCounts(0, 4, 0)),
    ],
)
def test_win_loss_tie_counting_is_explicit(
    changes: list[float], expected: temporal.ComparisonCounts
) -> None:
    assert temporal.comparison_counts(changes) == expected


@pytest.mark.parametrize("change", ["fingerprint", "boundary"])
def test_source_and_frozen_split_drift_fail(temporal_data: pd.DataFrame, change: str) -> None:
    config = make_split_config(temporal_data, DIGEST)
    if change == "boundary":
        config = replace(config, train=replace(config.train, end=config.validation.start))
    with pytest.raises(ValueError):
        temporal.run_experiment(
            temporal_data, config, dataset_sha256="b" * 64 if change == "fingerprint" else DIGEST
        )


def test_cli_records_only_original_training_predictions_and_preserves_inputs(
    temporal_data: pd.DataFrame, tmp_path: Path
) -> None:
    dataset = tmp_path / "synthetic.csv"
    raw = temporal_data.copy(deep=True)
    raw["date"] = raw["date"].dt.strftime("%m/%d/%Y")
    raw.to_csv(dataset, index=False)
    config = make_split_config(temporal_data, fingerprint(dataset))
    config_path = tmp_path / "split.json"
    save_split_config(config, config_path)
    source_bytes, config_bytes = dataset.read_bytes(), config_path.read_bytes()
    output = tmp_path / "audit.json"
    args = ["--dataset", str(dataset), "--split-config", str(config_path), "--output"]
    assert temporal.main([*args, str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["experiment"] == "EXP-004"
    assert payload["split_config_sha256"] == fingerprint(config_path)
    result = payload["result"]
    assert len(result["folds"]) == 4
    assert max(result["out_of_fold"]["dates"]) <= config.train.end
    assert dataset.read_bytes() == source_bytes and config_path.read_bytes() == config_bytes
    for protected in (dataset, config_path):
        before = protected.read_bytes()
        assert temporal.main([*args, str(protected)]) == 2
        assert protected.read_bytes() == before
    dataset.write_text(
        dataset.read_text(encoding="utf-8").replace(",sewing,", ",sewing ,"), encoding="utf-8"
    )
    output_bytes = output.read_bytes()
    assert temporal.main([*args, str(output)]) == 2
    assert output.read_bytes() == output_bytes
