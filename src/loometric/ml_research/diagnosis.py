"""Matched historical diagnosis using authorized labels and outcome-free context only."""

from itertools import combinations

import numpy as np
import pandas as pd

from loometric.ml_research.inspection import keyed_seed, paired_errors
from loometric.prediction.contracts import read_json
from loometric.synthetic_ml.storage import digest
from loometric.synthetic_training.data import NUMERIC, _json_rows, fingerprint, require
from loometric.synthetic_training.metrics import analyze, error_summary
from loometric.synthetic_training.risk import band_diagnostics


def context_projection(directory, data) -> pd.DataFrame:
    manifest = read_json((directory / "manifest.json").read_text(encoding="utf-8"))
    expected = manifest["files"]["features.jsonl"]["sha256"]
    require(
        digest(manifest) == data.provenance["manifest_fingerprint"]
        and fingerprint(directory / "features.jsonl") == expected,
        "CONTEXT_SOURCE_INTEGRITY_REQUIRED",
    )
    ids = set(data.train.X.index) | set(data.validation.X.index)
    selected = {}
    for row in _json_rows(directory / "features.jsonl"):
        if row["observation_id"] in ids:
            context = row["context"]
            require(
                set(context) == {"factory_id", "line_id", "crew_id", "style_id"},
                "DECLARED_CONTEXT_ONLY",
            )
            selected[row["observation_id"]] = context
    require(set(selected) == ids, "COMPLETE_DIAGNOSTIC_CONTEXT_REQUIRED")
    require(
        fingerprint(directory / "features.jsonl") == expected, "CONTEXT_SOURCE_INTEGRITY_REQUIRED"
    )
    # Outcome-free context is an audit axis, never a model feature matrix.
    return pd.DataFrame.from_dict(selected, orient="index")


def support_counts(metadata: pd.DataFrame, context: pd.DataFrame) -> dict:
    joined = metadata.join(context, how="left")
    require(not joined[list(context)].isna().any().any(), "ALIGNED_CONTEXT_REQUIRED")
    result = {}
    for stage, group in joined.groupby("stage", sort=True):
        result[str(stage)] = {
            "rows": len(group),
            "dates": int(group.start_date.nunique()),
            **{f"distinct_{c}": int(group[c].nunique()) for c in context},
        }
    return result


def interaction_errors(population, prediction: pd.Series) -> dict:
    metadata = population.metadata.copy()
    X = population.X.loc[metadata.index]
    for name, value in {
        "stage_workload": metadata.stage.astype(str) + "|" + metadata.workload_band.astype(str),
        "stage_shift": metadata.stage.astype(str) + "|" + metadata.shift_kind.astype(str),
        "skill_complexity": X.skill_level.astype(int).astype(str)
        + "|"
        + X.style_complexity.astype(int).astype(str),
    }.items():
        metadata[name] = value
    return {
        column: {
            str(key): {
                **error_summary(population.y.loc[index], prediction.loc[index]),
                "low_support": len(index) < 30,
            }
            for key, index in metadata.groupby(column, sort=True).groups.items()
        }
        for column in ("stage_workload", "stage_shift", "skill_complexity")
    }


def feature_audit(population) -> dict:
    X = population.X
    corr = X.loc[:, NUMERIC].corr(method="spearman")
    strong = [
        {"left": a, "right": b, "spearman": float(corr.loc[a, b])}
        for a, b in combinations(NUMERIC, 2)
        if np.isfinite(corr.loc[a, b]) and abs(corr.loc[a, b]) >= 0.9
    ]
    return {
        "rows": len(X),
        "constant_predictors": [c for c in X if X[c].nunique() == 1],
        "distinct_values": {c: int(X[c].nunique()) for c in X},
        "stock_sum_identity_rows": int(
            (X.opening_wip_pieces + X.planned_release_pieces == X.order_quantity).sum()
        ),
        "available_plus_downtime_450_rows": int(
            (X.available_minutes + X.planned_downtime_minutes == 450).sum()
        ),
        "strong_numeric_spearman_pairs": strong,
        "demand_censored_rows": int(population.metadata.demand_censored.sum()),
        "demand_censoring_role": "OUTCOME_DIAGNOSTIC_ONLY_NOT_PREDICTOR",
        "rare_difficult_event_flags": "NOT_OBSERVED_GLOBAL_OUTCOME_VALUES_NOT_DECODED",
    }


def matched_predictions(data, rows: list[dict], case: str, name: str) -> pd.Series:
    selected = [r for r in rows if r["case"] == case and r["model"] == name]
    require(
        len(selected) == len(data.validation.X)
        and len({r["observation_id"] for r in selected}) == len(selected),
        "EXACT_RETAINED_OBSERVATIONS_REQUIRED",
    )
    table = pd.DataFrame(selected).set_index("observation_id")
    require(set(table.index) == set(data.validation.X.index), "RETAINED_OBSERVATION_SET_DRIFT")
    table = table.loc[data.validation.X.index]
    require(
        np.array_equal(table.actual.to_numpy(), data.validation.y.to_numpy()),
        "RETAINED_TARGET_DRIFT",
    )
    return table.prediction.astype("float64")


def historical_diagnosis(
    datasets: dict, contexts: dict, rows: list[dict], original: dict, config: dict
) -> dict:
    result, predictions = {}, {}
    for case, data in datasets.items():
        base = (
            case
            if case.endswith("-baseline")
            else case.removesuffix("-disruption").removesuffix("-workload_surge") + "-baseline"
        )
        models = {
            name: matched_predictions(data, rows, case, name) for name in config["references"]
        }
        predictions[case] = models
        reports = {}
        for name, predicted in models.items():
            reports[name] = analyze(data.validation.y, predicted, data.validation.metadata)
            reports[name]["interactions"] = interaction_errors(data.validation, predicted)
            reports[name]["historical_band"] = band_diagnostics(
                data.validation.y,
                predicted,
                data.validation.metadata,
                original["residual_references"][base][name],
            )
            reports[name]["predictions_above_offered_work_ceiling"] = int(
                (predicted - data.validation.metadata.planned_load_ratio > 1e-12).sum()
            )
            require(
                reports[name]["overall"] == original["validation"][case][name]["overall"],
                "HISTORICAL_METRIC_REPRODUCTION_FAILURE",
            )
        pairs = {}
        for left, right in combinations(config["references"], 2):
            groups = {
                "all": data.validation.X.index,
                **{
                    f"stage:{s}": ids
                    for s, ids in data.validation.metadata.groupby(
                        "stage", sort=True
                    ).groups.items()
                },
            }
            pairs[left + "_vs_" + right] = {
                str(group): paired_errors(
                    data.validation.y.loc[ids],
                    models[left].loc[ids],
                    models[right].loc[ids],
                    data.validation.metadata.loc[ids],
                    seed=keyed_seed(config["resampling_seed"], case + left + right + str(group)),
                    repeats=config["bootstrap"]["repeats"],
                )
                for group, ids in groups.items()
            }
        result[case] = {
            "models": reports,
            "matched_pairs": pairs,
            "validation_support": support_counts(
                data.validation.metadata, contexts[case].loc[data.validation.X.index]
            ),
            "training_support": support_counts(
                data.train.metadata, contexts[case].loc[data.train.X.index]
            ),
            "training_features": feature_audit(data.train),
            "validation_features": feature_audit(data.validation),
        }
    hidden = {}
    for case, data in datasets.items():
        if not case.endswith("-disruption"):
            continue
        base = case.removesuffix("-disruption") + "-baseline"
        other = datasets[base]
        require(
            data.validation.X.equals(other.validation.X),
            "DECLARED_HIDDEN_SHIFT_INPUT_IDENTITY_REQUIRED",
        )
        delta = (data.validation.y - other.validation.y).abs()
        require(
            all(
                predictions[case][name].equals(predictions[base][name])
                for name in config["references"]
            ),
            "SAME_INPUT_SAME_FROZEN_PREDICTION_REQUIRED",
        )
        hidden[case] = {
            "matched_rows": len(delta),
            "identical_feature_vectors": True,
            "identical_reference_predictions": True,
            "mean_absolute_target_change": float(delta.mean()),
            "balanced_pair_empirical_mae_lower_bound": float(delta.mean() / 2),
            "balanced_pair_empirical_rmse_lower_bound": float(np.sqrt(np.mean(delta**2)) / 2),
            "interpretation": "BALANCED_PAIRED_SAMPLE_BOUND_NOT_UNIVERSAL_BAYES_ERROR",
        }
    return {
        "cases": result,
        "hidden_shift_pairs": hidden,
        "validation_role": "SPENT_DIAGNOSTIC_ONLY_NOT_SELECTION_OR_FRESH_CONFIRMATION",
    }
