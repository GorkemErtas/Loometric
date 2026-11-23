"""Held-out predictive sensitivity, coherent permutations and matched date resampling."""

import hashlib

import numpy as np
import pandas as pd

from loometric.synthetic_ml.features import FEATURE_COLUMNS
from loometric.synthetic_training.data import require
from loometric.synthetic_training.metrics import error_summary


def keyed_seed(seed: int, key: str) -> int:
    return int.from_bytes(hashlib.sha256(f"{seed}|{key}".encode()).digest()[:8], "big")


def paired_errors(
    actual: pd.Series,
    left: pd.Series,
    right: pd.Series,
    metadata: pd.DataFrame,
    *,
    seed: int,
    repeats: int = 500,
) -> dict:
    require(
        actual.index.equals(left.index)
        and actual.index.equals(right.index)
        and actual.index.equals(metadata.index),
        "EXACT_MATCHED_COMPARISON_REQUIRED",
    )
    delta = (left - actual).abs() - (right - actual).abs()
    grouped = (
        pd.DataFrame({"date": metadata.start_date, "delta": delta})
        .groupby("date", sort=True)
        .delta.agg(["sum", "count"])
    )
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(grouped), size=(repeats, len(grouped)))
    bootstrap = grouped["sum"].to_numpy()[draws].sum(axis=1) / grouped["count"].to_numpy()[
        draws
    ].sum(axis=1)
    return {
        "samples": len(actual),
        "dates": len(grouped),
        "left": error_summary(actual, left),
        "right": error_summary(actual, right),
        "mae_difference_left_minus_right": float(delta.mean()),
        "descriptive_date_bootstrap_interval": list(np.quantile(bootstrap, [0.025, 0.975])),
        "bootstrap_repeats": repeats,
        "interpretation": "DATE_RESAMPLING_NOT_INDEPENDENT_CREW_OR_FACTORY_CONFIDENCE",
        "left_absolute_error_wins": int(delta.lt(-1e-12).sum()),
        "ties": int(delta.abs().le(1e-12).sum()),
    }


def permutation_probe(
    model, population, evaluation_ids, *, seed: int, key: str, policy: dict
) -> dict:
    # Deterministic sample selection is independent of labels, predictions and
    # model identity. Both raw trees receive the same shuffled records.
    index = sorted(
        evaluation_ids, key=lambda oid: hashlib.sha256(f"{seed}|{key}|{oid}".encode()).digest()
    )[: policy["max_evaluation_rows"]]
    X, y = population.X.loc[index], population.y.loc[index]
    metadata = population.metadata.loc[index]
    base = float(np.mean(np.abs(model.predict(X) - y)))
    groups = {c: (c,) for c in FEATURE_COLUMNS}
    groups.update(
        {
            "joint_demand": ("opening_wip_pieces", "planned_release_pieces", "order_quantity"),
            "joint_capacity": (
                "planned_workers",
                "available_minutes",
                "planned_downtime_minutes",
                "planned_machine_available",
            ),
        }
    )
    results = {}
    for group, columns in groups.items():
        increases, invalid, changed = [], [], []
        for repeat in range(policy["repeats"]):
            rng = np.random.default_rng(keyed_seed(seed, f"{key}|{group}|{repeat}"))
            shuffled = X.copy()
            for day in sorted(set(metadata.start_date)):
                ids = metadata.index[metadata.start_date.eq(day)]
                order = rng.permutation(len(ids))
                shuffled.loc[ids, list(columns)] = X.loc[ids, list(columns)].to_numpy()[order]
            increases.append(float(np.mean(np.abs(model.predict(shuffled) - y))) - base)
            invalid.append(
                float(
                    (
                        (
                            shuffled.opening_wip_pieces + shuffled.planned_release_pieces
                            != shuffled.order_quantity
                        )
                        | (shuffled.available_minutes + shuffled.planned_downtime_minutes != 450)
                    ).mean()
                )
            )
            changed.append(
                float(shuffled.loc[:, list(columns)].ne(X.loc[:, list(columns)]).any(axis=1).mean())
            )
        results[group] = {
            "columns": list(columns),
            "mae_increases": increases,
            "mean_mae_increase": float(np.mean(increases)),
            "repeat_std": float(np.std(increases, ddof=1)) if len(increases) > 1 else 0.0,
            "known_physical_inconsistency_fraction": float(np.mean(invalid)),
            "changed_row_fraction": float(np.mean(changed)),
            "identifiable_under_block_scheme": any(v > 0 for v in changed),
        }
    return {
        "rows": len(index),
        "evaluation_ids_sha256": hashlib.sha256("\n".join(index).encode()).hexdigest(),
        "unpermuted_mae": base,
        "groups": results,
        "scope": "HELD_OUT_ORIGINAL_TRAINING_FOLD_ONLY",
        "intervention_or_causality_claim": False,
        "weekday_note": "Weekday is constant within date; zero change is unidentifiable, "
        "not evidence of irrelevance.",
    }


def impurity_probe(model) -> dict:
    preprocess = model.named_steps["preprocess"]
    totals = {name: 0.0 for name in FEATURE_COLUMNS}
    for encoded, value in zip(
        preprocess.get_feature_names_out(),
        model.named_steps["regression"].feature_importances_,
        strict=True,
    ):
        matches = [
            name
            for name in FEATURE_COLUMNS
            if encoded == f"numeric__{name}" or encoded.startswith(f"categorical__{name}_")
        ]
        require(len(matches) == 1, "RAW_IMPORTANCE_FEATURE_MAPPING_REQUIRED")
        totals[matches[0]] += float(value)
    return totals
