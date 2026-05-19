import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

import loometric.experiments.linear as linear
from loometric.data.loading import load_validated_csv
from loometric.data.profiling import fingerprint
from loometric.data.schema import TARGET
from loometric.data.splitting import (
    DEFAULT_CONFIG,
    apply_split_config,
    load_split_config,
    make_split_config,
    save_split_config,
)
from loometric.evaluation import RegressionMetrics
from loometric.experiments.naive import run_experiment as run_naive
from loometric.features import FEATURE_SETS, SOURCE_COLUMNS

DIGEST = "a" * 64


def test_pipeline_fitting_and_scoring_only_use_correct_partitions(
    chronological_data: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = make_split_config(chronological_data, DIGEST)
    splits = apply_split_config(chronological_data, config, dataset_sha256=DIGEST)
    # There is deliberately no .test property: accessing it would fail.
    development = SimpleNamespace(train=splits.train, validation=splits.validation)
    monkeypatch.setattr(linear, "apply_split_config", lambda *args, **kwargs: development)
    original_fit, original_predict = Pipeline.fit, Pipeline.predict
    original_score, original_features = linear.regression_metrics, linear.build_features
    fits, predictions, scored, built = [], [], [], []

    def fit(self: Pipeline, features: pd.DataFrame, target: pd.Series) -> Pipeline:
        assert features.index.equals(splits.train.index)
        assert target.equals(splits.train[TARGET])
        assert TARGET not in features
        fits.append(len(features))
        return original_fit(self, features, target)

    def predict(self: Pipeline, features: pd.DataFrame) -> object:
        assert features.index.equals(splits.validation.index)
        predictions.append(len(features))
        return original_predict(self, features)

    def score(actual: pd.Series, predicted: pd.Series) -> RegressionMetrics:
        assert set(actual.index).issubset(set(splits.validation.index))
        scored.append(len(actual))
        return original_score(actual, predicted)

    def features(scheduled: pd.DataFrame) -> pd.DataFrame:
        assert set(scheduled.columns) == set(SOURCE_COLUMNS)
        assert set(scheduled.index).isdisjoint(set(splits.test.index))
        built.append(len(scheduled))
        return original_features(scheduled)

    monkeypatch.setattr(Pipeline, "fit", fit)
    monkeypatch.setattr(Pipeline, "predict", predict)
    monkeypatch.setattr(linear, "regression_metrics", score)
    monkeypatch.setattr(linear, "build_features", features)
    result = linear.run_experiment(chronological_data, config, dataset_sha256=DIGEST)
    assert fits == [12] * 4 and predictions == [4] * 4
    assert built == [12, 4] and scored
    # Wednesday is present only in validation, never in the training vocabulary.
    calendar = result.models["department_team_calendar"]
    assert "2" not in calendar.training_categories["day_of_week"]
    assert calendar.unknown_validation_categories["day_of_week"] == 2


def test_heldout_targets_cannot_change_parameters_or_development_results(
    chronological_data: pd.DataFrame,
) -> None:
    config = make_split_config(chronological_data, DIGEST)
    expected = linear.run_experiment(chronological_data, config, dataset_sha256=DIGEST)
    changed = chronological_data.copy(deep=True)
    mask = changed["date"].ge(config.test.start)
    changed.loc[mask, TARGET] = float("nan")
    changed.loc[mask, "team"] = 99999
    changed.loc[mask, "department"] = "test-only-category"
    assert linear.run_experiment(changed, config, dataset_sha256=DIGEST) == expected


def test_validation_labels_do_not_change_training_categories_or_predictions(
    chronological_data: pd.DataFrame,
) -> None:
    config = make_split_config(chronological_data, DIGEST)
    expected = linear.run_experiment(chronological_data, config, dataset_sha256=DIGEST)
    changed = chronological_data.copy(deep=True)
    changed.loc[changed["date"].between(config.validation.start, config.validation.end), TARGET] = 9
    actual = linear.run_experiment(changed, config, dataset_sha256=DIGEST)
    for name, original in expected.models.items():
        model = actual.models[name]
        assert model.training_categories == original.training_categories
        assert model.diagnostics.prediction_min == original.diagnostics.prediction_min
        assert model.diagnostics.prediction_max == original.diagnostics.prediction_max
        assert model.metrics != original.metrics


def test_disallowed_columns_have_no_effect_and_baselines_match_exp001(
    chronological_data: pd.DataFrame,
) -> None:
    config = make_split_config(chronological_data, DIGEST)
    expected = linear.run_experiment(chronological_data, config, dataset_sha256=DIGEST)
    minimal = chronological_data.loc[:, (*SOURCE_COLUMNS, TARGET)]
    assert linear.run_experiment(minimal, config, dataset_sha256=DIGEST) == expected
    baselines = run_naive(chronological_data, config, dataset_sha256=DIGEST)
    for name, metrics in baselines.validation_metrics.items():
        assert expected.models[name].metrics == metrics


def test_reproducible_metrics_and_declared_feature_comparisons(
    chronological_data: pd.DataFrame,
) -> None:
    config = make_split_config(chronological_data, DIGEST)
    first = linear.run_experiment(chronological_data, config, dataset_sha256=DIGEST)
    assert linear.run_experiment(chronological_data, config, dataset_sha256=DIGEST) == first
    assert len(first.models) == 6
    for name, columns in FEATURE_SETS:
        model = first.models[name]
        assert model.columns == columns
        assert model.metrics.samples == config.validation.rows
        assert sum(model.diagnostics.residual_bins.values()) == model.metrics.samples
        assert model.training_seconds >= 0 and model.inference_seconds >= 0
        for reference, change in first.baseline_comparisons[name].items():
            assert change == linear.mae_change(
                model.metrics.mae, first.models[reference].metrics.mae
            )


def test_mae_changes_match_hand_calculations_and_handle_zero_reference() -> None:
    assert linear.mae_change(0.15, 0.2).absolute == pytest.approx(-0.05)
    assert linear.mae_change(0.15, 0.2).relative_percent == pytest.approx(-25)
    assert linear.mae_change(0.25, 0.2).relative_percent == pytest.approx(25)
    assert linear.mae_change(0.0, 0.0).relative_percent is None


def test_diagnostics_preserve_out_of_range_predictions_without_clipping() -> None:
    actual = pd.Series([0.0, 0.5, 1.0])
    predicted = pd.Series([-0.2, 0.5, 1.4])
    diagnostics = linear.prediction_diagnostics(actual, predicted, pd.Series([0.1, 0.9]))
    assert diagnostics.below_zero == diagnostics.above_one == 1
    assert diagnostics.outside_training_target_range == 2
    assert diagnostics.prediction_min == -0.2 and diagnostics.prediction_max == 1.4
    assert diagnostics.residual_quantiles["0.5"] == 0
    assert diagnostics.residual_std == pytest.approx(pd.Series([-0.2, 0, 0.4]).std(ddof=0))
    assert sum(diagnostics.residual_bins.values()) == 3


@pytest.mark.parametrize("change", ["fingerprint", "boundary"])
def test_experiment_rejects_source_or_split_drift(
    chronological_data: pd.DataFrame, change: str
) -> None:
    config = make_split_config(chronological_data, DIGEST)
    if change == "boundary":
        config = replace(config, validation=replace(config.validation, start=config.train.end))
    with pytest.raises(ValueError):
        linear.run_experiment(
            chronological_data,
            config,
            dataset_sha256="b" * 64 if change == "fingerprint" else DIGEST,
        )


def test_frozen_real_split_identity_and_boundaries_remain_unchanged() -> None:
    path = Path(__file__).resolve().parents[1] / DEFAULT_CONFIG
    assert fingerprint(path) == "c38de7e418b1d75a0d4e51ceec63344675afd8acc3de34d85e88315bd686a727"
    config = load_split_config(path)
    assert (
        config.train.end,
        config.validation.start,
        config.validation.end,
        config.test.start,
    ) == ("2015-02-10", "2015-02-11", "2015-02-25", "2015-02-26")
    assert (config.train.rows, config.validation.rows, config.test.rows) == (711, 232, 254)


def test_cli_keeps_source_split_and_exp001_report_unchanged(
    chronological_csv: Path,
    tmp_path: Path,
) -> None:
    data, _ = load_validated_csv(chronological_csv)
    config_path = tmp_path / "split.json"
    save_split_config(make_split_config(data, fingerprint(chronological_csv)), config_path)
    original_source, original_config = chronological_csv.read_bytes(), config_path.read_bytes()
    output = tmp_path / "result.json"
    args = ["--dataset", str(chronological_csv), "--split-config", str(config_path), "--output"]
    assert linear.main([*args, str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["experiment"] == "EXP-002"
    assert "test" not in payload["result"]["models"]
    assert payload["split_config_sha256"] == fingerprint(config_path)
    assert all(model["metrics"]["samples"] == 4 for model in payload["result"]["models"].values())
    assert chronological_csv.read_bytes() == original_source
    assert config_path.read_bytes() == original_config
    for protected in (chronological_csv, config_path):
        original = protected.read_bytes()
        assert linear.main([*args, str(protected)]) == 2
        assert protected.read_bytes() == original
    chronological_csv.write_text(
        chronological_csv.read_text(encoding="utf-8").replace(",sewing,", ",sewing ,"),
        encoding="utf-8",
    )
    original_output = output.read_bytes()
    assert linear.main([*args, str(output)]) == 2
    assert output.read_bytes() == original_output
