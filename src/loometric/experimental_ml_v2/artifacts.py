"""Verify the frozen research candidate before deserialization."""

import io
import json

from loometric.experimental_ml.artifacts import (
    ArtifactError,
    _read,
    sha256,
)
from loometric.experimental_ml_v2.constants import (
    ARTIFACT_DIRECTORY,
    MAX_MODEL_BYTES,
    MODEL_NAME,
    MODEL_STATUS,
    SOURCE_MANIFEST_SHA256,
    SOURCE_MODEL_SHA256,
    TRUSTED_MANIFEST_SHA256,
    VERSION,
)


def verified_bundle() -> tuple[dict, bytes]:
    """Verify exact artifact bytes without executing the model."""

    try:
        directory = ARTIFACT_DIRECTORY

        if directory.resolve() != directory.absolute():
            raise ArtifactError()

        manifest_bytes = _read(directory, "manifest.json", 1024 * 1024)

        if sha256(manifest_bytes) != TRUSTED_MANIFEST_SHA256:
            raise ArtifactError()

        manifest = json.loads(manifest_bytes)

        expected_files = {
            "metadata.json",
            "rf_physics.joblib",
        }

        if (
            manifest["schema_version"] != 1
            or manifest["model_version"] != VERSION
            or manifest["model"] != MODEL_NAME
            or set(manifest["files"]) != expected_files
            or manifest["promotion_decision"] != "NO_ML_PROMOTION"
            or manifest["serving_authorized"] is not False
            or manifest["reserved_labels_decoded"] is not False
            or manifest["capacity_application_authorized"] is not False
        ):
            raise ArtifactError()

        metadata_bytes = _read(directory, "metadata.json", 1024 * 1024)

        model_bytes = _read(directory, "rf_physics.joblib", MAX_MODEL_BYTES)

        if (
            sha256(metadata_bytes) != manifest["files"]["metadata.json"]
            or sha256(model_bytes) != manifest["files"]["rf_physics.joblib"]
            or sha256(model_bytes) != SOURCE_MODEL_SHA256
        ):
            raise ArtifactError()

        metadata = json.loads(metadata_bytes)

        from loometric.ml_research.artifacts import code_identity
        from loometric.synthetic_ml.features import FEATURE_COLUMNS
        from loometric.synthetic_training.artifacts import environment

        if (
            metadata["schema_version"] != 1
            or metadata["model"] != MODEL_NAME
            or metadata["model_version"] != VERSION
            or metadata["model_status"] != MODEL_STATUS
            or metadata["source_experiment"] != "EXP-008"
            or metadata["source_manifest_sha256"] != SOURCE_MANIFEST_SHA256
            or metadata["source_model_sha256"] != SOURCE_MODEL_SHA256
            or metadata["feature_order"] != list(FEATURE_COLUMNS)
            or metadata["environment"] != environment()
            or metadata["research_code"] != code_identity()
            or metadata["training_partition"] != "train"
            or metadata["dataset_version"] != "synthetic-ml-v1"
            or metadata["target"] != "standard_capacity_attainment"
            or metadata["experimental_only"] is not True
            or metadata["serving_authorized"] is not False
            or metadata["promotion_decision"] != "NO_ML_PROMOTION"
            or metadata["reserved_labels_decoded"] is not False
            or metadata["capacity_application_authorized"] is not False
        ):
            raise ArtifactError()

        return metadata, model_bytes

    except (OSError, ValueError, KeyError, TypeError, ImportError):
        raise ArtifactError() from None


def load_trusted_offline() -> tuple[dict, object]:
    """Load the verified candidate for offline testing only."""

    metadata, model_bytes = verified_bundle()

    import joblib
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.pipeline import Pipeline

    from loometric.ml_research.features import PlannedFeatures
    from loometric.synthetic_training.models import SchemaGuard

    try:
        model = joblib.load(io.BytesIO(model_bytes))

        if (
            not isinstance(model, Pipeline)
            or list(model.named_steps)
            != [
                "schema",
                "planned_features",
                "preprocess",
                "regression",
            ]
            or not isinstance(model.named_steps["schema"], SchemaGuard)
            or not isinstance(
                model.named_steps["planned_features"],
                PlannedFeatures,
            )
            or not isinstance(
                model.named_steps["regression"],
                RandomForestRegressor,
            )
        ):
            raise ArtifactError()

        return metadata, model

    except Exception:
        raise ArtifactError() from None
