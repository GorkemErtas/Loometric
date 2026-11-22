"""Synthetic saved constants verify inspection; none are real model evidence."""

import copy
import json
from dataclasses import asdict, replace

import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

from loometric.compatibility.cli import main
from loometric.compatibility.inspection import inspect_saved_predictions
from loometric.data.loading import clean_data
from loometric.data.profiling import fingerprint
from loometric.data.schema import TARGET
from loometric.data.splitting import apply_split_config, make_split_config, save_split_config
from loometric.data.temporal import DEFAULT_POLICY, make_expanding_folds
from loometric.error_analysis import ANALYZED_MODELS
from loometric.evaluation import regression_metrics
from loometric.experiments.errors import FROZEN_FEATURES, FROZEN_FOREST
from loometric.features import CATEGORICAL_FEATURES, SOURCE_COLUMNS, build_features
from loometric.forest import build_forest_pipeline
from loometric.linear import build_linear_pipeline


@pytest.fixture
def saved_inputs(raw_data, tmp_path):
    records = []
    for number, date in enumerate(pd.date_range("2015-01-01", periods=59)):
        for department in range(2):
            record = raw_data.iloc[department].copy()
            record["date"], record["day"] = date.strftime("%m/%d/%Y"), date.day_name()
            record[TARGET] = str(0.3 + number * 0.005 + department * 0.1)
            records.append(record)
    raw = pd.DataFrame(records, dtype="string").reset_index(drop=True)
    source = clean_data(raw)
    dataset, split, saved = (tmp_path / name for name in ("source.csv", "split.json", "saved.json"))
    raw.to_csv(dataset, index=False)
    config = make_split_config(source, fingerprint(dataset))
    save_split_config(config, split)
    training = apply_split_config(source, config, dataset_sha256=config.dataset_sha256).train
    features = build_features(training.loc[:, SOURCE_COLUMNS])
    folds = make_expanding_folds(training, config.train)
    evaluation = pd.concat(
        [
            training.loc[training["date"].between(f.evaluation.start, f.evaluation.end)]
            for f in folds
        ]
    )
    columns = {
        "department_mean": ("department",),
        "linear_A": FROZEN_FEATURES["A"],
        "forest_B_RF-01": FROZEN_FEATURES["B"],
    }
    parameters = {
        "department_mean": {},
        "linear_A": build_linear_pipeline(columns["linear_A"])
        .named_steps["regression"]
        .get_params(),
        "forest_B_RF-01": build_forest_pipeline(columns["forest_B_RF-01"], FROZEN_FOREST)
        .named_steps["regression"]
        .get_params(),
    }
    predictions = {
        name: pd.Series(0.6 + i * 0.05, index=evaluation.index)
        for i, name in enumerate(ANALYZED_MODELS)
    }
    artifact = {
        "experiment": "EXP-004",
        "split_config_sha256": fingerprint(split),
        "result": {
            "split": asdict(config),
            "policy": asdict(DEFAULT_POLICY),
            "folds": [],
            "pooled": {
                name: {"metrics": asdict(regression_metrics(evaluation[TARGET], values))}
                for name, values in predictions.items()
            },
            "out_of_fold": {
                "row_indices": list(evaluation.index),
                "dates": list(evaluation["date"].dt.strftime("%Y-%m-%d")),
                "departments": list(evaluation["department"].astype(str)),
                "actuals": list(evaluation[TARGET].astype(float)),
                "predictions": {name: list(values) for name, values in predictions.items()},
            },
        },
    }
    for fold in folds:
        prefix = training["date"].between(fold.train.start, fold.train.end)
        index = evaluation.index[
            evaluation["date"].between(fold.evaluation.start, fold.evaluation.end)
        ]
        models = {}
        for name, values in predictions.items():
            cats = {
                c: sorted(features.loc[prefix, c].unique().tolist())
                for c in columns[name]
                if c in CATEGORICAL_FEATURES
            }
            models[name] = {
                "columns": list(columns[name]),
                "estimator_parameters": parameters[name],
                "evaluation_metrics": asdict(
                    regression_metrics(evaluation.loc[index, TARGET], values.loc[index])
                ),
                "features": {
                    "training_categories": cats,
                    "unknown_validation_categories": {
                        c: int((~features.loc[index, c].isin(v)).sum()) for c, v in cats.items()
                    },
                },
            }
        artifact["result"]["folds"].append({"fold": asdict(fold), "models": models})
    saved.write_text(json.dumps(artifact), encoding="utf-8")
    return dataset, split, saved, config, artifact, raw


def inspect(inputs, **kwargs):
    return inspect_saved_predictions(
        *inputs[:3], expected_predictions_sha256=fingerprint(inputs[2]), **kwargs
    )


def test_metrics_provenance_determinism_and_no_estimator_execution(saved_inputs, monkeypatch):
    def prohibited(*args, **kwargs):
        raise AssertionError("Inspection cannot execute an estimator")

    import joblib

    monkeypatch.setattr(Pipeline, "fit", prohibited)
    monkeypatch.setattr(Pipeline, "predict", prohibited)
    monkeypatch.setattr(joblib, "load", prohibited)
    originals = {path: path.read_bytes() for path in saved_inputs[:3]}
    result = inspect(saved_inputs, include_observations=True)
    assert result == inspect(saved_inputs, include_observations=True)
    assert result["population_rows"] == 40
    assert result["observed_dates"] == 20
    assert len(result["observations"]) == 40
    assert max(row["row_index"] for row in result["observations"]) < saved_inputs[3].train.rows
    assert result["models_fitted"] == result["predictions_generated"] == 0
    assert result["outer_validation_evaluated"] is result["final_test_evaluated"] is False
    assert result["model_artifact_fingerprint"] is None
    assert result["source_artifact_sha256"] == fingerprint(saved_inputs[2])
    assert result["dataset_sha256"] == fingerprint(saved_inputs[0])
    for name in ANALYZED_MODELS:
        expected = saved_inputs[4]["result"]["pooled"][name]["metrics"]
        assert result["overall"][name]["metrics"] == pytest.approx(expected)
        errors = [r["predictions"][name] - r["actual"] for r in result["observations"]]
        assert result["overall"][name]["metrics"]["bias"] == pytest.approx(sum(errors) / 40)
    assert all(not any(row["unknown_categories"].values()) for row in result["category_coverage"])
    for path, content in originals.items():
        assert path.read_bytes() == content
    assert inspect(saved_inputs)["observations"] == []


def test_outer_labels_and_features_are_not_interpreted(saved_inputs):
    before = inspect(saved_inputs)
    dataset, split, saved, config, artifact, raw = saved_inputs
    raw = raw.copy(deep=True)
    outer = pd.to_datetime(raw["date"], format="%m/%d/%Y").gt(config.train.end)
    raw.loc[outer, TARGET] = "FINAL_LABEL_MUST_NOT_BE_PARSED"
    raw.loc[outer, "team"] = "NOT_A_NUMBER"
    raw.loc[outer, "department"] = "NOT_A_TRAINING_DEPARTMENT"
    raw.to_csv(dataset, index=False)
    changed_config = replace(config, dataset_sha256=fingerprint(dataset))
    split.write_text(json.dumps(asdict(changed_config)), encoding="utf-8")
    artifact["split_config_sha256"] = fingerprint(split)
    artifact["result"]["split"] = asdict(changed_config)
    saved.write_text(json.dumps(artifact), encoding="utf-8")
    after = inspect(saved_inputs)
    assert before["overall"] == after["overall"]
    assert before["department"] == after["department"]
    assert after["final_test_evaluated"] is False
    assert before["dataset_sha256"] != after["dataset_sha256"]


@pytest.mark.parametrize(
    "kind",
    [
        "digest",
        "actual",
        "final_date",
        "row_id",
        "fold",
        "metric",
        "vocabulary",
        "unknown_count",
        "parameters",
        "duplicate_key",
    ],
)
def test_drift_or_fabricated_evidence_is_rejected(saved_inputs, kind):
    _, _, saved, config, original, _ = saved_inputs
    expected = fingerprint(saved)
    artifact = copy.deepcopy(original)
    result, fold = artifact["result"], artifact["result"]["folds"][0]
    if kind == "actual":
        result["out_of_fold"]["actuals"][0] += 0.1
    elif kind == "final_date":
        result["out_of_fold"]["dates"][0] = config.test.start
    elif kind == "row_id":
        result["out_of_fold"]["row_indices"][0] = config.train.rows
    elif kind == "fold":
        fold["fold"]["evaluation"]["rows"] += 1
    elif kind == "metric":
        result["pooled"]["linear_A"]["metrics"]["mae"] += 0.1
    elif kind == "vocabulary":
        fold["models"]["linear_A"]["features"]["training_categories"]["team"] = ["unseen"]
    elif kind == "unknown_count":
        fold["models"]["linear_A"]["features"]["unknown_validation_categories"]["team"] += 1
    elif kind == "parameters":
        fold["models"]["forest_B_RF-01"]["estimator_parameters"]["max_depth"] = 99
    text = json.dumps(artifact)
    if kind == "digest":
        text += " "
    elif kind == "duplicate_key":
        text = '{"experiment":"EXP-004",' + text[1:]
    saved.write_text(text, encoding="utf-8")
    if kind != "digest":
        expected = fingerprint(
            saved
        )  # Even a newly trusted receipt cannot bypass alignment checks.
    with pytest.raises(ValueError):
        inspect_saved_predictions(*saved_inputs[:3], expected_predictions_sha256=expected)


def test_inspection_cli_creates_only_new_outputs(saved_inputs, tmp_path, capsys):
    dataset, split, saved = saved_inputs[:3]
    arguments = [
        "inspect-saved",
        "--dataset",
        str(dataset),
        "--split-config",
        str(split),
        "--predictions",
        str(saved),
        "--expected-predictions-sha256",
        fingerprint(saved),
    ]
    output = tmp_path / "audit.json"
    assert main([*arguments, "--include-observations", "--output", str(output)]) == 0
    assert json.loads(output.read_text())["observations_included"] is True
    originals = {path: path.read_bytes() for path in (*saved_inputs[:3], output)}
    for path, original in originals.items():
        assert main([*arguments, "--output", str(path)]) == 2
        assert path.read_bytes() == original
    capsys.readouterr()
    assert main([*arguments]) == 0
    assert json.loads(capsys.readouterr().out)["observations"] == []
