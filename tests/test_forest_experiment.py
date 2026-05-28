import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

import loometric.experiments.forest as forest
from loometric.data.loading import load_validated_csv
from loometric.data.profiling import fingerprint
from loometric.data.schema import TARGET
from loometric.data.splitting import (
    apply_split_config,
    make_split_config,
    save_split_config,
)
from loometric.evaluation import RegressionMetrics, regression_metrics
from loometric.experiments.linear import run_experiment as run_linear
from loometric.features import SOURCE_COLUMNS

DIGEST = "a" * 64


@pytest.fixture(autouse=True)
def small_synthetic_forests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test orchestration with short forests; production plan is asserted separately."""
    monkeypatch.setattr(
        forest,
        "FOREST_CONFIGURATIONS",
        tuple(replace(profile, n_estimators=5) for profile in forest.FOREST_CONFIGURATIONS),
    )


def test_fit_prediction_features_and_metrics_never_receive_final_test(
    chronological_data: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = make_split_config(chronological_data, DIGEST)
    splits = apply_split_config(chronological_data, config, dataset_sha256=DIGEST)
    development = SimpleNamespace(train=splits.train, validation=splits.validation)
    monkeypatch.setattr(forest, "apply_split_config", lambda *args, **kwargs: development)
    original_fit, original_predict = Pipeline.fit, Pipeline.predict
    original_features, original_metrics = forest.build_features, forest.regression_metrics
    fits, predictions, built, scored = [], [], [], []

    def fit(self: Pipeline, features: pd.DataFrame, target: pd.Series) -> Pipeline:
        assert features.index.equals(splits.train.index)
        assert target.equals(splits.train[TARGET])
        assert TARGET not in features
        fits.append(len(features))
        return original_fit(self, features, target)

    def predict(self: Pipeline, features: pd.DataFrame) -> object:
        assert features.index.equals(splits.train.index) or features.index.equals(
            splits.validation.index
        )
        predictions.append(len(features))
        return original_predict(self, features)

    def build(scheduled: pd.DataFrame) -> pd.DataFrame:
        assert set(scheduled.columns) == set(SOURCE_COLUMNS)
        assert set(scheduled.index).isdisjoint(set(splits.test.index))
        built.append(len(scheduled))
        return original_features(scheduled)

    def score(actual: pd.Series, predicted: pd.Series) -> RegressionMetrics:
        assert set(actual.index).isdisjoint(set(splits.test.index))
        assert set(actual.index).issubset(set(splits.train.index)) or set(actual.index).issubset(
            set(splits.validation.index)
        )
        scored.append(len(actual))
        return original_metrics(actual, predicted)

    monkeypatch.setattr(Pipeline, "fit", fit)
    monkeypatch.setattr(Pipeline, "predict", predict)
    monkeypatch.setattr(forest, "build_features", build)
    monkeypatch.setattr(forest, "regression_metrics", score)
    result = forest.run_experiment(chronological_data, config, dataset_sha256=DIGEST)
    assert fits == [12] * 8
    assert predictions == [12, 4] * 8
    assert built == [12, 4] and scored
    assert len(result.forests) == 6 and len(result.references) == 4
    for name, model in result.forests.items():
        if name.startswith("B_"):
            assert "2" not in model.features.training_categories["day_of_week"]
            assert model.features.unknown_validation_categories["day_of_week"] == 2


def test_final_test_poisoning_and_disallowed_source_fields_cannot_change_results(
    chronological_data: pd.DataFrame,
) -> None:
    config = make_split_config(chronological_data, DIGEST)
    expected = forest.run_experiment(chronological_data, config, dataset_sha256=DIGEST)
    changed = chronological_data.copy(deep=True)
    mask = changed["date"].ge(config.test.start)
    changed.loc[mask, TARGET] = float("nan")
    changed.loc[mask, "team"] = 999
    changed.loc[mask, "department"] = "test-only"
    assert forest.run_experiment(changed, config, dataset_sha256=DIGEST) == expected
    minimal = chronological_data.loc[:, (*SOURCE_COLUMNS, TARGET)]
    assert forest.run_experiment(minimal, config, dataset_sha256=DIGEST) == expected


def test_validation_outcomes_do_not_affect_training_or_fitted_predictions(
    chronological_data: pd.DataFrame,
) -> None:
    config = make_split_config(chronological_data, DIGEST)
    expected = forest.run_experiment(chronological_data, config, dataset_sha256=DIGEST)
    changed = chronological_data.copy(deep=True)
    changed.loc[changed["date"].between(config.validation.start, config.validation.end), TARGET] = 8
    actual = forest.run_experiment(changed, config, dataset_sha256=DIGEST)
    for name, before in expected.forests.items():
        after = actual.forests[name]
        assert after.training_mae == before.training_mae
        assert after.features == before.features
        assert after.impurity_importance == before.impurity_importance
        assert after.diagnostics.prediction_min == before.diagnostics.prediction_min
        assert after.diagnostics.prediction_max == before.diagnostics.prediction_max
        assert after.validation_metrics != before.validation_metrics


def test_reproducible_experiment_and_backward_compatible_reference_results(
    chronological_data: pd.DataFrame,
) -> None:
    config = make_split_config(chronological_data, DIGEST)
    result = forest.run_experiment(chronological_data, config, dataset_sha256=DIGEST)
    assert forest.run_experiment(chronological_data, config, dataset_sha256=DIGEST) == result
    previous = run_linear(chronological_data, config, dataset_sha256=DIGEST)
    for current, old in (
        ("global_mean", "global_mean"),
        ("department_mean", "department_mean"),
        ("linear_A", "department_team"),
        ("linear_B", "department_team_calendar"),
    ):
        assert result.references[current].validation_metrics == previous.models[old].metrics
        assert result.references[current].department_mae == previous.models[old].department_mae
    for name, model in result.forests.items():
        assert model.training_mae >= 0
        assert model.validation_metrics.samples == config.validation.rows
        assert model.validation_minus_training_mae == pytest.approx(
            model.validation_metrics.mae - model.training_mae
        )
        change = result.comparisons[name]["department_mean"]
        reference = result.references["department_mean"].validation_metrics.mae
        assert change.absolute == pytest.approx(model.validation_metrics.mae - reference)
        assert change.relative_percent == pytest.approx(100 * change.absolute / reference)
        assert model.impurity_importance is not None
        assert sum(model.diagnostics.residual_bins.values()) == config.validation.rows
        assert model.training_seconds >= 0 and model.inference_seconds >= 0
    best_score = result.forests[result.best_forest].validation_metrics.mae
    assert best_score == min(model.validation_metrics.mae for model in result.forests.values())


def test_aggregate_and_department_metrics_match_independent_sklearn_calculation(
    chronological_data: pd.DataFrame,
) -> None:
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    from loometric.forest import build_forest_pipeline

    config = make_split_config(chronological_data, DIGEST)
    splits = apply_split_config(chronological_data, config, dataset_sha256=DIGEST)
    columns = forest.FOREST_FEATURE_SETS[1][1]
    pipeline = build_forest_pipeline(columns, forest.FOREST_CONFIGURATIONS[2])
    train_x = forest.build_features(splits.train.loc[:, SOURCE_COLUMNS]).loc[:, columns]
    val_x = forest.build_features(splits.validation.loc[:, SOURCE_COLUMNS]).loc[:, columns]
    pipeline.fit(train_x, splits.train[TARGET])
    predicted = pd.Series(pipeline.predict(val_x), index=splits.validation.index)
    actual = splits.validation[TARGET]
    result = forest.run_experiment(chronological_data, config, dataset_sha256=DIGEST)
    score = result.forests["B_RF-03"]
    assert score.training_mae == pytest.approx(
        mean_absolute_error(splits.train[TARGET], pipeline.predict(train_x))
    )
    assert score.validation_metrics.mae == pytest.approx(mean_absolute_error(actual, predicted))
    assert score.validation_metrics.rmse == pytest.approx(
        mean_squared_error(actual, predicted) ** 0.5
    )
    assert score.validation_metrics.r2 == pytest.approx(r2_score(actual, predicted))
    assert score.validation_metrics.bias == pytest.approx(float((predicted - actual).mean()))
    for department, group in splits.validation.groupby("department"):
        assert score.department_mae[department] == pytest.approx(
            mean_absolute_error(group[TARGET], predicted.loc[group.index])
        )


@pytest.mark.parametrize(
    ("scores", "baseline", "expected"),
    [
        ({"A": 0.12, "B": 0.11}, 0.14, ("B", "B")),
        ({"A": 0.15, "B": 0.16}, 0.14, ("A", "department_mean")),
        ({"A": 0.14, "B": 0.14}, 0.14, ("A", "department_mean")),
        ({"A": 0.14, "B": 0.14 - 1e-13}, 0.15, ("A", "A")),
        ({"A": 0.14 - 1e-13}, 0.14, ("A", "department_mean")),
    ],
)
def test_selection_uses_validation_mae_and_retains_baseline_on_no_improvement(
    scores: dict[str, float], baseline: float, expected: tuple[str, str]
) -> None:
    assert forest.select_preferred_model(scores, baseline) == expected


@pytest.mark.parametrize("scores", [{}, {"A": float("nan")}, {"A": -0.1}])
def test_selection_rejects_invalid_validation_metrics(scores: dict[str, float]) -> None:
    with pytest.raises(ValueError, match="Selection"):
        forest.select_preferred_model(scores, 0.14)


@pytest.mark.parametrize("change", ["fingerprint", "boundary"])
def test_experiment_preserves_split_verification(
    chronological_data: pd.DataFrame, change: str
) -> None:
    config = make_split_config(chronological_data, DIGEST)
    if change == "boundary":
        config = replace(config, validation=replace(config.validation, start=config.train.end))
    with pytest.raises(ValueError):
        forest.run_experiment(
            chronological_data,
            config,
            dataset_sha256="b" * 64 if change == "fingerprint" else DIGEST,
        )


def test_cli_preserves_inputs_and_records_only_development_metrics(
    chronological_csv: Path, tmp_path: Path
) -> None:
    data, _ = load_validated_csv(chronological_csv)
    config_path = tmp_path / "split.json"
    save_split_config(make_split_config(data, fingerprint(chronological_csv)), config_path)
    original_data, original_config = chronological_csv.read_bytes(), config_path.read_bytes()
    output = tmp_path / "forest.json"
    arguments = [
        "--dataset",
        str(chronological_csv),
        "--split-config",
        str(config_path),
        "--output",
    ]
    assert forest.main([*arguments, str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["experiment"] == "EXP-003"
    assert payload["random_state"] == 42 and payload["n_jobs"] == 1
    assert payload["split_config_sha256"] == fingerprint(config_path)
    assert len(payload["result"]["forests"]) == 6
    for model in payload["result"]["forests"].values():
        assert model["validation_metrics"]["samples"] == 4
    assert chronological_csv.read_bytes() == original_data
    assert config_path.read_bytes() == original_config
    for protected in (chronological_csv, config_path):
        before = protected.read_bytes()
        assert forest.main([*arguments, str(protected)]) == 2
        assert protected.read_bytes() == before
    chronological_csv.write_text(
        chronological_csv.read_text(encoding="utf-8").replace(",sewing,", ",sewing ,"),
        encoding="utf-8",
    )
    original_output = output.read_bytes()
    assert forest.main([*arguments, str(output)]) == 2
    assert output.read_bytes() == original_output


def test_exp002_keeps_public_diagnostic_imports() -> None:
    import loometric.evaluation as evaluation
    import loometric.experiments.linear as linear

    assert linear.mae_change is evaluation.mae_change
    assert linear.prediction_diagnostics is evaluation.prediction_diagnostics
    assert linear.RegressionMetrics is evaluation.RegressionMetrics
    assert regression_metrics(pd.Series([1, 2]), pd.Series([2, 2])).mae == 0.5
