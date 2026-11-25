"""Versioned experimental inference with separate provenance."""

from itertools import combinations
from math import isfinite

import pandas as pd
from threadpoolctl import threadpool_limits

from loometric.api.prediction_schemas import SyntheticPredictionRequest
from loometric.api.prediction_schemas_v2 import SyntheticPredictionRequestV2
from loometric.experimental_ml.artifacts import (
    ArtifactError,
    canonical,
    sha256,
)
from loometric.experimental_ml.inference import (
    predict as predict_v1,
)
from loometric.experimental_ml_v2.constants import (
    SUPPORT_PROFILE_SHA256,
    TRAINING_FINGERPRINT,
    TRUSTED_MANIFEST_SHA256,
    VERSION,
)
from loometric.synthetic_ml.features import FEATURE_COLUMNS
from loometric.synthetic_training.risk import assess_support


def predict_v2(
    request: SyntheticPredictionRequestV2,
    metadata: dict,
    models: dict,
    receipt: str,
    research_model: object | None,
) -> dict:
    inputs = request.inputs.model_dump()

    row = {
        **inputs,
        "weekday": str(inputs["weekday"]),
        "planned_machine_available": int(inputs["planned_machine_available"]),
    }

    frame = pd.DataFrame(
        [row],
        columns=FEATURE_COLUMNS,
    )

    if "rf_physics" in request.models:
        training = metadata["training"]
        if (
            metadata["dataset_version"] != "synthetic-ml-v1"
            or metadata["target"] != "standard_capacity_attainment"
            or training["partition"] != "train"
            or training["case"] != "benchmark-42-baseline"
            or training["source"]["train_fingerprint"] != TRAINING_FINGERPRINT
            or sha256(canonical(metadata["support"])) != SUPPORT_PROFILE_SHA256
        ):
            raise ArtifactError()

    legacy_names = [name for name in request.models if name != "rf_physics"]

    # The v1 predictor also builds the shared response envelope. Its internal
    # empty-model call supports a candidate-only request without running a legacy
    # estimator; public v1 requests still require at least one model.
    legacy_request = SyntheticPredictionRequest.model_construct(
        schema_version=1,
        synthetic=True,
        prediction_context=request.prediction_context,
        inputs=request.inputs,
        models=legacy_names,
    )

    response = predict_v1(legacy_request, metadata, models, receipt)

    results = {result["model"]: result for result in response["results"]}

    if "rf_physics" in request.models:
        support = assess_support(
            row,
            metadata["support"],
        )

        value = None

        if support["status"] != "ABSTAIN":
            with threadpool_limits(limits=1):
                raw = float(research_model.predict(frame)[0])

            support = assess_support(
                row,
                metadata["support"],
                raw,
            )

            if support["status"] != "ABSTAIN" and isfinite(raw):
                value = raw

        results["rf_physics"] = {
            "model": "rf_physics",
            "identity": "rf_physics",
            "model_version": VERSION,
            "model_status": "RESEARCH_CANDIDATE",
            "prediction": value,
            "support": support,
            "descriptive_band": None,
            "validation_metrics": {
                "mae": 0.057931364704274735,
                "rmse": 0.09936276695864536,
                "r2": 0.8206691735917163,
                "samples": 4833,
            },
            "validation_stage_metrics": None,
            "promotion_checks": None,
            "global_feature_importance": None,
            "explanation_method": "NOT_COMPUTED",
            "provenance": {
                "experiment_id": "EXP-008",
                "manifest_sha256": (TRUSTED_MANIFEST_SHA256),
                "validation_rows": 4833,
                "fresh_validation": False,
                "support_profile_source": ("V1_BENCHMARK_TRAINING"),
            },
        }

    ordered = [results[name] for name in request.models]

    response["schema_version"] = 2
    response["results"] = ordered

    response["differences"] = [
        {
            "left": a["model"],
            "right": b["model"],
            "left_minus_right": (
                None
                if a["prediction"] is None or b["prediction"] is None
                else a["prediction"] - b["prediction"]
            ),
        }
        for a, b in combinations(ordered, 2)
    ]

    response["provenance"]["research_candidate"] = (
        {
            "model": "rf_physics",
            "experiment_id": "EXP-008",
            "manifest_sha256": (TRUSTED_MANIFEST_SHA256),
            "fresh_validation": False,
        }
        if "rf_physics" in request.models
        else None
    )

    response["input_fingerprint"] = sha256(canonical(inputs))

    response["limitations"] = [
        *response["limitations"],
        "RF Physics metrics use spent benchmark validation.",
        "RF Physics has no independently calibrated prediction band.",
        "Hidden disruption risk remains unresolved.",
    ]

    return response
