"""Explicit local experimental serving policy."""

from loometric.api.prediction_schemas_v2 import SyntheticPredictionRequestV2
from loometric.experimental_ml.artifacts import ArtifactError
from loometric.experimental_ml_v2.artifacts import (
    load_trusted_offline,
)

EXPERIMENTAL_SERVING_RECEIPT = {
    "manifest_sha256": ("55b09223c57e6c52261a71bc777edddc6116b88b8ffae3f7b0f9cc9075cc51f0"),
    "model": "rf_physics",
    "model_version": "synthetic-experimental-v2",
    "source_experiment": "EXP-008",
    "prediction_context": "HYPOTHETICAL_PRE_SHIFT",
    "experimental_api_authorized": True,
    "production_serving_authorized": False,
    "capacity_application_authorized": False,
    "promotion_decision": "NO_ML_PROMOTION",
}


def load_experimental_model(contract: SyntheticPredictionRequestV2) -> tuple[dict, object]:
    from loometric.experimental_ml_v2.constants import (
        TRUSTED_MANIFEST_SHA256,
    )

    policy = EXPERIMENTAL_SERVING_RECEIPT

    if (
        policy.get("model") != "rf_physics"
        or policy.get("model_version") != "synthetic-experimental-v2"
        or policy.get("source_experiment") != "EXP-008"
        or policy.get("promotion_decision") != "NO_ML_PROMOTION"
        or policy.get("prediction_context") != "HYPOTHETICAL_PRE_SHIFT"
        or policy.get("manifest_sha256") != TRUSTED_MANIFEST_SHA256
        or policy.get("experimental_api_authorized") is not True
        or policy.get("production_serving_authorized") is not False
        or policy.get("capacity_application_authorized") is not False
        or contract.schema_version != 2
        or contract.synthetic is not True
        or contract.prediction_context != policy["prediction_context"]
        or policy["model"] not in contract.models
    ):
        raise ArtifactError()

    metadata, model = load_trusted_offline()

    for key in (
        "model",
        "model_version",
        "source_experiment",
        "promotion_decision",
    ):
        if metadata.get(key) != policy[key]:
            raise ArtifactError()

    if (
        metadata.get("experimental_only") is not True
        or metadata.get("capacity_application_authorized") is not False
        or metadata.get("serving_authorized") is not False
    ):
        raise ArtifactError()

    return metadata, model
