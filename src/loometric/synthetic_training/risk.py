"""Train-only support and descriptive OOF residual bands; no calibrated coverage claim."""

from math import isfinite

import numpy as np
import pandas as pd

from loometric.synthetic_ml.features import FEATURE_COLUMNS
from loometric.synthetic_training.data import CATEGORICAL, NUMERIC


def support_profile(X: pd.DataFrame, y: pd.Series) -> dict:
    return {
        "categories": {c: sorted(set(X[c])) for c in CATEGORICAL},
        "numeric_bounds": {
            c: {"minimum": float(X[c].min()), "maximum": float(X[c].max())} for c in NUMERIC
        },
        "training_label_minimum": float(y.min()),
        "training_label_maximum": float(y.max()),
        "entity_generalization": "RESERVED_EVALUATION_DEFERRED",
        "capacity_application_authorized": False,
    }


def assess_support(inputs: dict, profile: dict, prediction: float | None = None) -> dict:
    codes, abstain = [], False
    if set(inputs) != set(FEATURE_COLUMNS):
        return {"status": "ABSTAIN", "reason_codes": ["EXACT_FEATURE_SCHEMA_REQUIRED"]}
    if any(str(inputs[c]) not in profile["categories"][c] for c in CATEGORICAL):
        codes.append("UNSUPPORTED_CATEGORICAL_INPUT")
        abstain = True
    numbers = {}
    for column in NUMERIC:
        try:
            if isinstance(inputs[column], bool) and column != "planned_machine_available":
                raise ValueError("Boolean count")
            numbers[column] = float(inputs[column])
            if not isfinite(numbers[column]):
                raise ValueError("Nonfinite")
        except (ValueError, TypeError, OverflowError):
            return {"status": "ABSTAIN", "reason_codes": ["INVALID_NUMERIC_INPUT"]}
    n = numbers
    if (
        n["planned_workers"] <= 0
        or n["available_minutes"] <= 0
        or n["planned_machine_available"] == 0
    ):
        return {"status": "ABSTAIN", "reason_codes": ["ZERO_PLANNED_CAPACITY_UNDEFINED_TARGET"]}
    if (
        not 0 < n["standard_worker_minutes_per_piece"] <= 100
        or not 0 < n["planned_workers"] <= 100
        or not 1 <= n["skill_level"] <= 5
        or not 1 <= n["style_complexity"] <= 5
        or not 0 < n["available_minutes"] <= 480
        or not 0 <= n["planned_downtime_minutes"] <= 480
        or n["order_quantity"] <= 0
        or min(n["opening_wip_pieces"], n["planned_release_pieces"]) < 0
        or n["opening_wip_pieces"] + n["planned_release_pieces"] != n["order_quantity"]
        or n["planned_machine_available"] != 1
        or any(n[c] != int(n[c]) for c in NUMERIC if c != "standard_worker_minutes_per_piece")
    ):
        return {"status": "ABSTAIN", "reason_codes": ["INVALID_OR_UNSUPPORTED_PHYSICAL_INPUT"]}
    for column, number in n.items():
        bounds = profile["numeric_bounds"][column]
        if not bounds["minimum"] <= number <= bounds["maximum"]:
            codes.append(f"OUTSIDE_TRAINING_SUPPORT:{column}")
    if prediction is not None:
        if not isfinite(prediction) or prediction < 0 or prediction > 3:
            codes.append("INVALID_OR_PHYSICALLY_UNSUPPORTED_PREDICTION")
            abstain = True
        elif (
            not profile["training_label_minimum"] <= prediction <= profile["training_label_maximum"]
        ):
            codes.append("PREDICTION_OUTSIDE_TRAINING_LABEL_SUPPORT")
    return {
        "status": "ABSTAIN"
        if abstain
        else "REVIEW_REQUIRED"
        if codes
        else "SUPPORTED_EXPERIMENTAL",
        "reason_codes": codes or ["WITHIN_DECLARED_FEATURE_SUPPORT_ONLY"],
    }


def residual_reference(rows: list[dict]) -> dict:
    errors = [abs(r["prediction"] - r["actual"]) for r in rows]
    if not errors or not all(isfinite(v) for v in errors):
        raise ValueError("FINITE_TRAINING_OOF_RESIDUALS_REQUIRED")
    global_radius = float(np.quantile(errors, 0.9))
    stages = {}
    for stage in sorted({r["stage"] for r in rows}):
        values = [abs(r["prediction"] - r["actual"]) for r in rows if r["stage"] == stage]
        stages[stage] = {
            "samples": len(values),
            "radius": float(np.quantile(values, 0.9)) if len(values) >= 30 else global_radius,
            "fallback_to_global": len(values) < 30,
        }
    return {
        "interpretation": "DEVELOPMENT_RESIDUAL_BAND_NOT_CALIBRATED",
        "quantile": 0.9,
        "samples": len(errors),
        "global_radius": global_radius,
        "stage_radii": stages,
        "coverage_guarantee": False,
        "selection_reused_calibration_folds": True,
    }


def band_diagnostics(
    actual: pd.Series, prediction: pd.Series, metadata: pd.DataFrame, reference: dict
) -> dict:
    radii = pd.Series(
        [
            reference["stage_radii"].get(stage, {"radius": reference["global_radius"]})["radius"]
            for stage in metadata.stage
        ],
        index=actual.index,
    )
    covered = (prediction - actual).abs().le(radii)
    return {
        "samples": len(actual),
        "covered": int(covered.sum()),
        "empirical_coverage": float(covered.mean()),
        "mean_width": float((2 * radii).mean()),
        "coverage_guarantee": False,
        "interval_endpoints_clipped": False,
        "reference": reference["interpretation"],
    }
