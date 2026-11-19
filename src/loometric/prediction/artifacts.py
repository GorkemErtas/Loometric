"""Explicit training and trusted-local persistence, never invoked by inference."""

import hashlib
import io
import json
import pickle
import platform
import zlib
from dataclasses import asdict, dataclass
from importlib.metadata import version
from math import isfinite
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

from loometric.baselines import DepartmentMeanBaseline
from loometric.data.loading import clean_data, read_csv
from loometric.data.profiling import fingerprint
from loometric.data.schema import TARGET
from loometric.data.splitting import apply_split_config, load_split_config
from loometric.data.validation import validate_data
from loometric.features import SOURCE_COLUMNS, build_features
from loometric.forest import FOREST_CONFIGURATIONS, FOREST_FEATURE_SETS, build_forest_pipeline
from loometric.prediction.contracts import ContractError, read_json
from loometric.preprocessing import inspect_preprocessor

MODEL_ID = "B_RF-01"
MODEL_VERSION = "m01-v1"
FEATURE_SCHEMA_VERSION = 1
FEATURE_COLUMNS = dict(FOREST_FEATURE_SETS)["B"]


class ArtifactError(ContractError):
    """A missing, incompatible or untrusted artifact must produce abstention."""


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def environment() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "platform": platform.system(),
        **{
            name: version(name)
            for name in (
                "loometric",
                "pandas",
                "numpy",
                "scipy",
                "scikit-learn",
                "joblib",
                "threadpoolctl",
            )
        },
    }


def model_configuration() -> dict[str, Any]:
    pipeline = build_forest_pipeline(FEATURE_COLUMNS, FOREST_CONFIGURATIONS[0])
    return {
        "model_id": MODEL_ID,
        "model_version": MODEL_VERSION,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "features": list(FEATURE_COLUMNS),
        "regression": pipeline.named_steps["regression"].get_params(deep=False),
        "preprocessing": {
            "categorical": ["department", "team", "day_of_week"],
            "numeric": ["day_of_month"],
            "encoder": "OneHotEncoder",
            "handle_unknown": "ignore",
            "drop": None,
            "sparse_output": False,
            "remainder": "drop",
        },
    }


def load_training_partition(dataset: Path, split_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Verify dates/hash first; only retain, normalize and validate training labels.

    Outer-partition dates are needed to verify the frozen split. No outer outcomes
    are converted, validated, returned or evaluated. Raw CSV structure/bytes are scanned.
    """
    source_hash = fingerprint(dataset)
    split_hash = fingerprint(split_path)
    config = load_split_config(split_path)
    if source_hash != config.dataset_sha256:
        raise ValueError("Dataset fingerprint differs from the frozen split configuration.")
    dates = clean_data(read_csv(dataset, columns=("date",)))
    dates["source_row"] = range(len(dates))
    split = apply_split_config(dates, config, dataset_sha256=source_hash)
    selected = frozenset(int(value) for value in split.train["source_row"])
    raw = read_csv(dataset, row_indices=selected)
    training = clean_data(raw)
    validation = validate_data(raw, training)
    if not validation.passed:
        raise ValueError(
            "Training data validation failed: "
            + "; ".join(issue.message for issue in validation.issues if issue.severity == "error")
        )
    if fingerprint(dataset) != source_hash or fingerprint(split_path) != split_hash:
        raise ValueError("Dataset or split changed during training-data loading.")
    lineage = {
        "dataset_sha256": source_hash,
        "split_file_sha256": split_hash,
        "strategy": config.strategy,
        "training": asdict(config.train),
    }
    lineage["training_split_fingerprint"] = digest(lineage)
    return training.sort_values("date", kind="stable").reset_index(drop=True), lineage


def generate_artifact(dataset: Path, split_path: Path, destination: Path) -> dict[str, Any]:
    """Fit exactly once on the verified original training partition; refuse overwrite."""
    if destination.exists():
        raise FileExistsError(f"Artifact destination already exists: {destination}")
    training, lineage = load_training_partition(dataset, split_path)
    features = build_features(training.loc[:, SOURCE_COLUMNS])
    pipeline = build_forest_pipeline(FEATURE_COLUMNS, FOREST_CONFIGURATIONS[0])
    pipeline.fit(features, training[TARGET])
    baseline = DepartmentMeanBaseline.fit(training["department"], training[TARGET])
    metadata = inspect_preprocessor(pipeline.named_steps["preprocessing"], features)
    buffer = io.BytesIO()
    joblib.dump(pipeline, buffer, compress=3, protocol=5)
    model_bytes = buffer.getvalue()
    configuration = model_configuration()
    manifest = {
        "artifact_schema_version": 1,
        "input_schema_version": 1,
        "configuration": configuration,
        "model_configuration_fingerprint": digest(configuration),
        "lineage": lineage,
        "environment": environment(),
        "training_categories": metadata.training_categories,
        "encoded_columns": metadata.encoded_columns,
        "baseline": asdict(baseline),
        "pipeline_sha256": hashlib.sha256(model_bytes).hexdigest(),
    }
    # Encode before creating the destination; an interrupted write will fail closed on loading.
    manifest_bytes = canonical_json(manifest)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "pipeline.joblib").write_bytes(model_bytes)
    (destination / "manifest.json").write_bytes(manifest_bytes + b"\n")
    return {"artifact_fingerprint": digest(manifest), "manifest": manifest}


@dataclass(frozen=True)
class LoadedArtifact:
    pipeline: Pipeline
    baseline: DepartmentMeanBaseline
    manifest: dict[str, Any]
    artifact_fingerprint: str


def load_artifact(directory: Path, *, expected_fingerprint: str) -> LoadedArtifact:
    """Load only a trusted local artifact with an independently retained manifest digest.

    Joblib uses pickle: hashes detect drift, not malicious publishers. The caller must
    trust the generator and obtain expected_fingerprint from its output, not this directory.
    All byte hashes, versions and metadata are checked BEFORE deserialization.
    """
    try:
        manifest = read_json((directory / "manifest.json").read_text(encoding="utf-8"))
        actual = digest(manifest)
        if not expected_fingerprint or actual != expected_fingerprint:
            raise ArtifactError("ARTIFACT_FINGERPRINT_MISMATCH", "Manifest fingerprint differs.")
        if (
            type(manifest["artifact_schema_version"]) is not int
            or manifest["artifact_schema_version"] != 1
            or type(manifest["input_schema_version"]) is not int
            or manifest["input_schema_version"] != 1
        ):
            raise ArtifactError("ARTIFACT_SCHEMA_MISMATCH", "Incompatible artifact/input schema.")
        configuration = model_configuration()
        if manifest["configuration"] != configuration or manifest[
            "model_configuration_fingerprint"
        ] != digest(configuration):
            raise ArtifactError(
                "MODEL_CONFIGURATION_MISMATCH", "Artifact is not the fixed B_RF-01 contract."
            )
        if manifest["environment"] != environment():
            raise ArtifactError(
                "ARTIFACT_ENVIRONMENT_MISMATCH", "Reproduce the artifact environment exactly."
            )
        lineage = dict(manifest["lineage"])
        claimed = lineage.pop("training_split_fingerprint")
        if claimed != digest(lineage):
            raise ArtifactError(
                "TRAINING_FINGERPRINT_MISMATCH", "Training lineage fingerprint differs."
            )
        model_bytes = (directory / "pipeline.joblib").read_bytes()
        if hashlib.sha256(model_bytes).hexdigest() != manifest["pipeline_sha256"]:
            raise ArtifactError("ARTIFACT_INTEGRITY_MISMATCH", "Pipeline byte fingerprint differs.")
        pipeline = joblib.load(io.BytesIO(model_bytes))
        if not isinstance(pipeline, Pipeline) or list(pipeline.named_steps) != [
            "preprocessing",
            "regression",
        ]:
            raise ValueError("Unexpected pipeline stages.")
        regression = pipeline.named_steps["regression"]
        expected_model = build_forest_pipeline(FEATURE_COLUMNS, FOREST_CONFIGURATIONS[0])
        if type(regression) is not type(expected_model.named_steps["regression"]):
            raise ValueError("Unexpected estimator type.")
        if regression.get_params(deep=False) != configuration["regression"]:
            raise ValueError("Serialized estimator parameters differ.")
        preprocessing = pipeline.named_steps["preprocessing"]
        expected_preprocessing = expected_model.named_steps["preprocessing"]
        if type(preprocessing) is not type(expected_preprocessing):
            raise ValueError("Serialized preprocessing configuration differs.")
        actual_params = preprocessing.get_params(deep=False)
        expected_params = expected_preprocessing.get_params(deep=False)
        if {k: v for k, v in actual_params.items() if k != "transformers"} != {
            k: v for k, v in expected_params.items() if k != "transformers"
        }:
            raise ValueError("Serialized preprocessing parameters differ.")
        actual_layout = [(name, list(columns)) for name, _, columns in preprocessing.transformers]
        expected_layout = [
            (name, list(columns)) for name, _, columns in expected_preprocessing.transformers
        ]
        if actual_layout != expected_layout:
            raise ValueError("Serialized feature selection differs.")
        expected_encoder = expected_preprocessing.transformers[0][1]
        encoder = preprocessing.named_transformers_["categorical"]
        if type(encoder) is not type(expected_encoder) or encoder.get_params(
            deep=False
        ) != expected_encoder.get_params(deep=False):
            raise ValueError("Serialized encoder configuration differs.")
        if list(preprocessing.get_feature_names_out()) != manifest["encoded_columns"]:
            raise ValueError("Encoded feature schema differs.")
        categories = {
            str(name): list(values)
            for name, values in zip(encoder.feature_names_in_, encoder.categories_, strict=True)
        }
        if categories != manifest["training_categories"]:
            raise ValueError("Training category metadata differs.")
        baseline = DepartmentMeanBaseline(**manifest["baseline"])
        if set(baseline.department_means) != {"sewing", "finishing"} or not all(
            isfinite(value) and value >= 0
            for value in [baseline.global_mean, *baseline.department_means.values()]
        ):
            raise ValueError("Invalid baseline metadata.")
        return LoadedArtifact(pipeline, baseline, manifest, actual)
    except ArtifactError:
        raise
    except FileNotFoundError as exc:
        raise ArtifactError(
            "ARTIFACT_MISSING", "Artifact manifest or pipeline is missing."
        ) from exc
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        EOFError,
        pickle.UnpicklingError,
        zlib.error,
        IndexError,
    ) as exc:
        raise ArtifactError("ARTIFACT_INVALID", f"Artifact validation failed: {exc}") from exc
