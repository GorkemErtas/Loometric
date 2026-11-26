"""Optional fifth model with explicit mature-context admission and matched held-out evidence."""

from itertools import combinations

import pandas as pd
from threadpoolctl import threadpool_limits

from loometric.api.prediction_schemas_v2 import SyntheticPredictionRequestV2
from loometric.api.prediction_schemas_v3 import SyntheticPredictionRequestV3
from loometric.experimental_ml.artifacts import canonical, sha256
from loometric.experimental_ml_v2.inference import predict_v2
from loometric.final_candidate.artifacts import (
    VERSION,
    load_trusted,
    trusted_policy,
    verified_bundle,
)
from loometric.final_candidate.model import MODEL_COLUMNS
from loometric.synthetic_training.risk import assess_support


def predict_v3(
    request: SyntheticPredictionRequestV3,
    metadata: dict,
    models: dict,
    receipt: str,
    research_model: object | None,
) -> dict:
    selected = [m for m in request.models if m != "history_boost"]
    base = SyntheticPredictionRequestV2.model_construct(
        schema_version=2,
        synthetic=True,
        prediction_context=request.prediction_context,
        models=selected,
        inputs=request.inputs,
    )
    response = predict_v2(base, metadata, models, receipt, research_model)
    response["schema_version"] = 3
    response["history"] = request.history.model_dump()
    response["provenance"]["history_candidate"] = None
    history = request.history.model_dump()
    inputs = request.inputs.model_dump()
    response["input_fingerprint"] = sha256(canonical({"inputs": inputs, "history": history}))
    if "history_boost" not in request.models:
        return response
    row = {
        **inputs,
        "weekday": str(inputs["weekday"]),
        "planned_machine_available": int(inputs["planned_machine_available"]),
    }
    # No legacy artifacts are overwritten and no model is fitted on this path.
    new_metadata, _ = verified_bundle()
    support = assess_support(row, new_metadata["input_profile"])
    ready = (
        history["uncensored_history_count"] >= 2
        and history["recent_attainment_mean"] is not None
        and history["history_age_hours"] is not None
        and history["history_age_hours"] <= 72
    )
    value = None
    if not ready:
        support = {
            "status": "ABSTAIN",
            "reason_codes": [
                *([] if support["status"] != "ABSTAIN" else support["reason_codes"]),
                "MATURE_HISTORY_REQUIRED",
            ],
        }
    elif support["status"] != "ABSTAIN":
        loaded, model = load_trusted()
        if loaded != new_metadata:
            from loometric.experimental_ml.artifacts import ArtifactError

            raise ArtifactError()
        with threadpool_limits(limits=1):
            raw = float(model.predict(pd.DataFrame([{**row, **history}], columns=MODEL_COLUMNS))[0])
        support = assess_support(row, new_metadata["input_profile"], raw)
        if support["status"] != "ABSTAIN":
            value = raw
            support = {
                "status": "REVIEW_REQUIRED",
                "reason_codes": [
                    *support["reason_codes"],
                    "HYPOTHETICAL_HISTORY_NOT_SOURCE_VERIFIED",
                ],
            }
    matched = new_metadata["comparisons"]
    candidate = {
        "model": "history_boost",
        "identity": "history_boost",
        "model_version": VERSION,
        "model_status": "EXPERIMENTAL_HISTORY_CANDIDATE",
        "prediction": value,
        "support": support,
        "descriptive_band": None,
        "validation_metrics": {
            k: matched["baseline"]["history_boost"][k] for k in ("mae", "rmse", "r2", "samples")
        },
        "validation_stage_metrics": None,
        "promotion_checks": None,
        "global_feature_importance": None,
        "explanation_method": "NOT_COMPUTED",
        "provenance": {
            "experiment_id": "EXP-010",
            "manifest_sha256": trusted_policy()["manifest_sha256"],
            "fresh_validation": False,
            "support_profile_source": "NEW_DEVELOPMENT_TRAINING_ONLY",
            "requires_mature_history": True,
        },
    }
    result_by_name = {r["model"]: r for r in response["results"]}
    result_by_name["history_boost"] = candidate
    for name, result in result_by_name.items():
        result["matched_metrics"] = {
            condition: {
                k: matched[condition][name][k]
                for k in (
                    "mae",
                    "rmse",
                    "r2",
                    "samples",
                    "bias",
                    "p95_absolute_error",
                    "actual_worst_absolute_error",
                )
            }
            for condition in ("baseline", "disruption")
        }
    response["results"] = [result_by_name[name] for name in request.models]
    response["differences"] = [
        {
            "left": a["model"],
            "right": b["model"],
            "left_minus_right": None
            if a["prediction"] is None or b["prediction"] is None
            else a["prediction"] - b["prediction"],
        }
        for a, b in combinations(response["results"], 2)
    ]
    response["input_fingerprint"] = sha256(canonical({"inputs": inputs, "history": history}))
    response["provenance"]["history_candidate"] = {
        "model": "history_boost",
        "experiment_id": "EXP-010",
        "manifest_sha256": trusted_policy()["manifest_sha256"],
        "fresh_validation": False,
        "matched_evaluation": "FOUR_NEW_WORLD_HELDOUT_ONLINE_MATURE_HISTORY",
        "training_rows": new_metadata["training"]["fit_rows"],
    }
    response["limitations"] += [
        "History Boost uses additional mature reports and new development data; "
        "this is not an algorithm-only comparison.",
        "EXP-010 metrics use equal-world macro averages and online history; "
        "inspected results are now spent.",
        "Missing/stale history abstains; the missing-history control was inferior "
        "to RF Physics under disruption.",
        "Baseline actual worst error increased 9.11% versus RF Physics; "
        "first unannounced shocks remain unpredictable.",
        "No calibrated candidate band, factory validation or operational promotion is established.",
    ]
    return response
