import copy
import json
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

import loometric.experiments.errors as errors
from loometric.data.loading import clean_data
from loometric.data.profiling import fingerprint
from loometric.data.schema import TARGET
from loometric.data.splitting import apply_split_config, make_split_config, save_split_config
from loometric.data.temporal import DEFAULT_POLICY, make_expanding_folds
from loometric.error_analysis import ANALYZED_MODELS
from loometric.evaluation import regression_metrics

DIGEST = "a" * 64
SPLIT_DIGEST = "b" * 64


@pytest.fixture
def source(raw_data: pd.DataFrame) -> pd.DataFrame:
    records = []
    for number, date in enumerate(pd.date_range("2015-01-01", periods=59)):
        for department in range(2):
            record = raw_data.iloc[department].copy()
            record["date"], record["day"] = date.strftime("%m/%d/%Y"), date.day_name()
            record[TARGET] = str(0.3 + number * 0.005 + department * 0.1)
            records.append(record)
    return clean_data(pd.DataFrame(records, dtype="string").reset_index(drop=True))


def artifact_for(
    source: pd.DataFrame, digest: str = DIGEST, split_digest: str = SPLIT_DIGEST
) -> dict:
    """Synthetic saved constants, never trained models or real experiment evidence."""
    config = make_split_config(source, digest)
    training = apply_split_config(source, config, dataset_sha256=digest).train
    folds = make_expanding_folds(training, config.train)
    frames = [
        training.loc[training["date"].between(fold.evaluation.start, fold.evaluation.end)]
        for fold in folds
    ]
    evaluation = pd.concat(frames)
    columns = {
        "department_mean": ("department",),
        "linear_A": errors.FROZEN_FEATURES["A"],
        "forest_B_RF-01": errors.FROZEN_FEATURES["B"],
    }
    params = {
        "department_mean": {},
        "linear_A": errors.build_linear_pipeline(columns["linear_A"])
        .named_steps["regression"]
        .get_params(),
        "forest_B_RF-01": errors.build_forest_pipeline(
            columns["forest_B_RF-01"], errors.FROZEN_FOREST
        )
        .named_steps["regression"]
        .get_params(),
    }
    predictions = {
        name: pd.Series(0.6 + number * 0.05, index=evaluation.index)
        for number, name in enumerate(ANALYZED_MODELS)
    }
    return {
        "experiment": "EXP-004",
        "split_config_sha256": split_digest,
        "result": {
            "split": asdict(config),
            "policy": asdict(DEFAULT_POLICY),
            "folds": [
                {
                    "fold": asdict(fold),
                    "models": {
                        name: {
                            "columns": list(columns[name]),
                            "estimator_parameters": params[name],
                            "evaluation_metrics": asdict(
                                regression_metrics(frame[TARGET], predicted.loc[frame.index])
                            ),
                        }
                        for name, predicted in predictions.items()
                    },
                }
                for fold, frame in zip(folds, frames, strict=True)
            ],
            "pooled": {
                name: {"metrics": asdict(regression_metrics(evaluation[TARGET], predicted))}
                for name, predicted in predictions.items()
            },
            "out_of_fold": {
                "row_indices": list(evaluation.index),
                "dates": list(evaluation["date"].dt.strftime("%Y-%m-%d")),
                "departments": list(evaluation["department"].astype(str)),
                "actuals": list(evaluation[TARGET].astype(float)),
                "predictions": {name: list(predicted) for name, predicted in predictions.items()},
            },
        },
    }


def test_saved_predictions_are_reused_without_any_model_fitting(
    source: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = make_split_config(source, DIGEST)
    artifact = artifact_for(source)
    splits = apply_split_config(source, config, dataset_sha256=DIGEST)
    monkeypatch.setattr(
        errors, "apply_split_config", lambda *args, **kwargs: SimpleNamespace(train=splits.train)
    )

    def prohibited_fit(*args, **kwargs):
        raise AssertionError("EXP-005 must never fit an estimator")

    monkeypatch.setattr(Pipeline, "fit", prohibited_fit)
    result = errors.run_experiment(
        source, config, artifact, dataset_sha256=DIGEST, split_sha256=SPLIT_DIGEST
    )
    assert result["population_rows"] == 40
    assert {entry["group"]["model"] for entry in result["summaries"]["overall"]} == set(
        ANALYZED_MODELS
    )
    assert result["target_distribution"]["samples"] == 40


def test_outer_holdout_poisoning_has_no_effect_and_outputs_are_reproducible(
    source: pd.DataFrame,
) -> None:
    config = make_split_config(source, DIGEST)
    artifact = artifact_for(source)
    expected = errors.run_experiment(
        source, config, artifact, dataset_sha256=DIGEST, split_sha256=SPLIT_DIGEST
    )
    changed = source.copy(deep=True)
    holdouts = changed["date"].gt(config.train.end)
    changed.loc[holdouts, TARGET] = float("nan")
    changed.loc[holdouts, "team"] = 999
    changed.loc[holdouts, "department"] = "outer-holdout-only"
    assert (
        errors.run_experiment(
            changed, config, artifact, dataset_sha256=DIGEST, split_sha256=SPLIT_DIGEST
        )
        == expected
    )
    assert (
        errors.run_experiment(
            source, config, artifact, dataset_sha256=DIGEST, split_sha256=SPLIT_DIGEST
        )
        == expected
    )


@pytest.mark.parametrize(
    "kind",
    [
        "experiment",
        "split_hash",
        "dataset_hash",
        "policy",
        "fold",
        "row_id",
        "date",
        "department",
        "actual",
        "prediction_length",
        "prediction_nan",
        "parameters",
        "columns",
        "pooled_metrics",
        "fold_metrics",
    ],
)
def test_stale_misaligned_or_modified_artifacts_are_rejected(
    source: pd.DataFrame, kind: str
) -> None:
    config = make_split_config(source, DIGEST)
    artifact = copy.deepcopy(artifact_for(source))
    result, oof = artifact["result"], artifact["result"]["out_of_fold"]
    if kind == "experiment":
        artifact["experiment"] = "EXP-003"
    elif kind == "split_hash":
        artifact["split_config_sha256"] = "c" * 64
    elif kind == "dataset_hash":
        result["split"]["dataset_sha256"] = "c" * 64
    elif kind == "policy":
        result["policy"]["evaluation_dates"] = 10
    elif kind == "fold":
        result["folds"][0]["fold"]["evaluation"]["rows"] += 1
    elif kind == "row_id":
        oof["row_indices"][0] = config.train.rows
    elif kind == "date":
        oof["dates"][0] = config.test.start
    elif kind == "department":
        oof["departments"][0] = "sewing" if oof["departments"][0] != "sewing" else "finishing"
    elif kind == "actual":
        oof["actuals"][0] += 0.01
    elif kind == "prediction_length":
        oof["predictions"]["linear_A"].pop()
    elif kind == "prediction_nan":
        oof["predictions"]["linear_A"][0] = float("nan")
    elif kind == "parameters":
        result["folds"][0]["models"]["forest_B_RF-01"]["estimator_parameters"]["max_depth"] = 10
    elif kind == "columns":
        result["folds"][0]["models"]["linear_A"]["columns"].append(TARGET)
    elif kind == "pooled_metrics":
        result["pooled"]["linear_A"]["metrics"]["mae"] += 0.01
    else:
        result["folds"][0]["models"]["linear_A"]["evaluation_metrics"]["mae"] += 0.01
    with pytest.raises(ValueError):
        errors.run_experiment(
            source, config, artifact, dataset_sha256=DIGEST, split_sha256=SPLIT_DIGEST
        )


@pytest.mark.parametrize("artifact", [{}, [], {"experiment": "EXP-004"}])
def test_malformed_artifacts_fail_deliberately(source: pd.DataFrame, artifact: dict) -> None:
    config = make_split_config(source, DIGEST)
    with pytest.raises(ValueError):
        errors.run_experiment(
            source, config, artifact, dataset_sha256=DIGEST, split_sha256=SPLIT_DIGEST
        )


@pytest.mark.parametrize("kind", ["fingerprint", "boundary"])
def test_existing_source_and_split_verification_is_preserved(
    source: pd.DataFrame, kind: str
) -> None:
    config = make_split_config(source, DIGEST)
    artifact = artifact_for(source)
    if kind == "boundary":
        config = replace(config, train=replace(config.train, end=config.validation.start))
    with pytest.raises(ValueError):
        errors.run_experiment(
            source,
            config,
            artifact,
            dataset_sha256="c" * 64 if kind == "fingerprint" else DIGEST,
            split_sha256=SPLIT_DIGEST,
        )


def test_cli_preserves_dataset_split_and_saved_predictions(
    source: pd.DataFrame, tmp_path: Path
) -> None:
    dataset = tmp_path / "source.csv"
    raw = source.copy(deep=True)
    raw["date"] = raw["date"].dt.strftime("%m/%d/%Y")
    raw.to_csv(dataset, index=False)
    dataset_hash = fingerprint(dataset)
    config = make_split_config(source, dataset_hash)
    config_path = tmp_path / "split.json"
    save_split_config(config, config_path)
    predictions_path = tmp_path / "exp-004.json"
    predictions_path.write_text(
        json.dumps(artifact_for(source, dataset_hash, fingerprint(config_path))), encoding="utf-8"
    )
    output = tmp_path / "exp-005.json"
    arguments = [
        "--dataset",
        str(dataset),
        "--split-config",
        str(config_path),
        "--predictions",
        str(predictions_path),
        "--output",
    ]
    originals = {path: path.read_bytes() for path in (dataset, config_path, predictions_path)}
    assert errors.main([*arguments, str(output)]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["experiment"] == "EXP-005"
    assert payload["source_artifact_sha256"] == fingerprint(predictions_path)
    assert payload["analysis"]["population_rows"] == 40
    for protected, original in originals.items():
        assert protected.read_bytes() == original
        assert errors.main([*arguments, str(protected)]) == 2
        assert protected.read_bytes() == original
    original_output = output.read_bytes()
    predictions_path.write_text("not json", encoding="utf-8")
    assert errors.main([*arguments, str(output)]) == 2
    assert output.read_bytes() == original_output


def test_missing_saved_predictions_do_not_trigger_refitting_or_replace_output(
    tmp_path: Path,
) -> None:
    output = tmp_path / "analysis.json"
    output.write_text("existing evidence", encoding="utf-8")
    assert (
        errors.main(["--predictions", str(tmp_path / "missing.json"), "--output", str(output)]) == 2
    )
    assert output.read_text(encoding="utf-8") == "existing evidence"
