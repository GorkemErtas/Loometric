"""Verify a closed artifact set before loading any executable bytes from memory."""

import hashlib
import io
import json
import re
from pathlib import Path

from loometric.experimental_ml.constants import ARTIFACT_ROOT, MODELS, VERSION


class ArtifactError(ValueError):
    """Fixed public failure; never disclose file names, pickle content or exception text."""

    def __init__(self):
        super().__init__("EXPERIMENTAL_ARTIFACT_UNAVAILABLE")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def _read(directory: Path, name: str, ceiling: int) -> bytes:
    path = directory / name
    # Resolve both directory and individual files; reject symlink/junction escapes.
    if path.resolve() != directory.resolve() / name or path.stat().st_size > ceiling:
        raise ArtifactError()
    with path.open("rb") as source:
        value = source.read(ceiling + 1)
    if len(value) > ceiling:
        raise ArtifactError()
    return value


def verified_bundle(directory: Path, receipt: str) -> tuple[dict, dict, dict[str, bytes]]:
    """Internal trusted configuration only; never exposed as a request parameter.

    Verify all bytes first. The exact checked byte buffers are subsequently loaded,
    closing the file replacement gap between digest verification and deserialization.
    """
    try:
        if re.fullmatch(r"[a-f0-9]{64}", receipt) is None:
            raise ArtifactError()
        manifest_bytes = _read(directory, "manifest.json", 1024 * 1024)
        if sha256(manifest_bytes) != receipt:
            raise ArtifactError()
        manifest = json.loads(manifest_bytes)
        expected = {
            "metadata.json",
            "random_forest.joblib",
            "histogram_gradient_boosting.joblib",
            "grouped_mean.json",
        }
        if (
            manifest["schema_version"] != 1
            or manifest["model_version"] != VERSION
            or set(manifest["files"]) != expected
            or manifest["promotion_decision"] != "NO_ML_PROMOTION"
            or manifest["reserved_labels_decoded"] is not False
            or manifest["capacity_application_authorized"] is not False
        ):
            raise ArtifactError()
        buffers = {name: _read(directory, name, 64 * 1024 * 1024) for name in sorted(expected)}
        if any(sha256(value) != manifest["files"][name] for name, value in buffers.items()):
            raise ArtifactError()
        metadata = json.loads(buffers["metadata.json"])
        from loometric.synthetic_ml.features import FEATURE_COLUMNS
        from loometric.synthetic_training.artifacts import environment

        if (
            metadata["environment"] != environment()
            or metadata["feature_order"] != list(FEATURE_COLUMNS)
            or set(metadata["models"]) != set(MODELS)
            or metadata["training"]["partition"] != "train"
            or metadata["training"]["rows"] <= 0
            or metadata["model_version"] != VERSION
            or metadata["promotion_decision"] != "NO_ML_PROMOTION"
        ):
            raise ArtifactError()
        return manifest, metadata, buffers
    except (OSError, ValueError, KeyError, TypeError, ImportError):
        raise ArtifactError() from None


def load_trusted(receipt: str, *, directory: Path | None = None) -> tuple[dict, dict]:
    # Only the in-process internal test seam accepts a directory. HTTP and CLI
    # inference never accept a path; production callers use this exact v1 location.
    directory = directory or ARTIFACT_ROOT / "v1"
    if directory.resolve() != directory.absolute():
        raise ArtifactError()
    _, metadata, buffers = verified_bundle(directory, receipt)
    import joblib
    from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
    from sklearn.pipeline import Pipeline

    from loometric.synthetic_training.models import MeanModel, model_metadata

    models = {}
    try:
        for name, estimator_type in (
            ("random_forest", RandomForestRegressor),
            ("histogram_gradient_boosting", HistGradientBoostingRegressor),
        ):
            model = joblib.load(io.BytesIO(buffers[f"{name}.joblib"]))
            if (
                not isinstance(model, Pipeline)
                or list(model.named_steps) != ["schema", "preprocess", "regression"]
                or not isinstance(model.named_steps["regression"], estimator_type)
                or model_metadata(model) != metadata["models"][name]["preprocessing"]
            ):
                raise ArtifactError()
            models[name] = model
        state = json.loads(buffers["grouped_mean.json"])
        baseline = MeanModel("grouped_mean")
        if state["model"] != "grouped_mean" or state["minimum_group_support"] != 10:
            raise ArtifactError()
        baseline.global_mean = state["global_mean"]
        baseline.groups = {
            tuple(group["columns"]): {
                tuple(row["key"]): (row["mean"], row["count"]) for row in group["values"]
            }
            for group in state["groups"]
        }
        if model_metadata(baseline) != metadata["models"]["grouped_mean"]["preprocessing"]:
            raise ArtifactError()
        models["grouped_mean"] = baseline
        return metadata, models
    except Exception:
        raise ArtifactError() from None
