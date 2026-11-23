"""Prediction only: same validated input vector for each explicitly selected model."""

from itertools import combinations
from math import isfinite

import pandas as pd
from threadpoolctl import threadpool_limits

from loometric.api.prediction_schemas import SyntheticPredictionRequest
from loometric.experimental_ml.artifacts import canonical, sha256
from loometric.experimental_ml.constants import LIMITATIONS, VERSION
from loometric.synthetic_ml.features import FEATURE_COLUMNS
from loometric.synthetic_training.risk import assess_support


def predict(
    request: SyntheticPredictionRequest, metadata: dict, models: dict, receipt: str
) -> dict:
    inputs = request.inputs.model_dump()
    # Training categorical weekdays are canonical strings; machine availability
    # is a numeric feature. Preserve JSON boolean/integer units in the public echo.
    row = {
        **inputs,
        "weekday": str(inputs["weekday"]),
        "planned_machine_available": int(inputs["planned_machine_available"]),
    }
    frame = pd.DataFrame([row], columns=FEATURE_COLUMNS)
    results = []
    with threadpool_limits(limits=1):
        for name in request.models:
            details = metadata["models"][name]
            support = assess_support(row, metadata["support"])
            value, band = None, None
            if support["status"] != "ABSTAIN":
                raw = float(models[name].predict(frame)[0])
                support = assess_support(row, metadata["support"], raw)
                if support["status"] != "ABSTAIN" and isfinite(raw):
                    value = raw
                    reference = details["residual_reference"]
                    stage = reference["stage_radii"].get(inputs["stage"])
                    radius = stage["radius"] if stage else reference["global_radius"]
                    band = {
                        "interpretation": reference["interpretation"],
                        "lower": raw - radius,
                        "upper": raw + radius,
                        "radius": radius,
                        "coverage_guarantee": False,
                        "source": "BENCHMARK_TRAINING_OOF_P90_ABSOLUTE_RESIDUALS",
                        "selection_reused_folds": True,
                        "empirical_benchmark_validation": details["validation"]["risk_band"],
                    }
            results.append(
                {
                    "model": name,
                    "identity": details["identity"],
                    "model_version": VERSION,
                    "model_status": details["status"],
                    "prediction": value,
                    "support": support,
                    "descriptive_band": band,
                    "validation_metrics": details["validation"]["overall"],
                    "validation_stage_metrics": details["validation"]["slices"]["stage"].get(
                        inputs["stage"]
                    ),
                    "promotion_checks": details["promotion_checks"],
                    "global_feature_importance": details["global_feature_importance"],
                    "explanation_method": details["explanation_method"],
                }
            )
    differences = [
        {
            "left": a["model"],
            "right": b["model"],
            "left_minus_right": None
            if a["prediction"] is None or b["prediction"] is None
            else a["prediction"] - b["prediction"],
        }
        for a, b in combinations(results, 2)
    ]
    return {
        "schema_version": 1,
        "synthetic": True,
        "prediction_context": request.prediction_context,
        "target": metadata["target"],
        "units": metadata["units"],
        "inputs": inputs,
        "input_fingerprint": sha256(canonical(inputs)),
        "results": results,
        "differences": differences,
        "provenance": {
            "manifest_sha256": receipt,
            "dataset_version": metadata["dataset_version"],
            "experiment_id": metadata["experiment_id"],
            "training": metadata["training"],
        },
        "promotion_decision": "NO_ML_PROMOTION",
        "limitations": LIMITATIONS,
        "capacity_application_authorized": False,
        "target_to_efficiency": "NOT_IMPLEMENTED",
    }
