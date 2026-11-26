"""Receipt-pinned offline loading; no fitting, calibration or serving entry points."""

from dataclasses import dataclass

from loometric.prediction.contracts import read_json
from loometric.prospective_evaluation.protocol import ROOT, load_protocol, verify_frozen_sources
from loometric.prospective_evaluation.source import require
from loometric.prospective_evaluation.storage import (
    MAX_FILE_BYTES,
    MAX_MANIFEST_BYTES,
    encode,
    read_checked,
    sha256,
)


@dataclass(frozen=True)
class FrozenModels:
    models: dict
    profile: dict
    receipts: dict


def verify_model_receipts(config: dict, repository=ROOT) -> dict:
    """Verify BOTH closed bundles before allowing any executable deserialization."""
    metadata = {}
    for name, bundle in config["frozen_bundles"].items():
        directory = repository / bundle["directory"]
        require(directory.resolve() == directory.absolute(), "FROZEN_MODEL_PATH_ESCAPE")
        require(
            {p.name for p in directory.iterdir()} == {"manifest.json", *bundle["files"]},
            "CLOSED_FROZEN_MODEL_BUNDLE_REQUIRED",
        )
        raw = read_checked(directory / "manifest.json", MAX_MANIFEST_BYTES)
        require(sha256(raw) == bundle["manifest_sha256"], "FROZEN_MODEL_MANIFEST_DRIFT")
        manifest = read_json(raw.decode())
        require(
            manifest["files"] == bundle["files"]
            and manifest["promotion_decision"] == "NO_ML_PROMOTION",
            "FROZEN_MODEL_POLICY_DRIFT",
        )
        for file, expected in bundle["files"].items():
            content = read_checked(directory / file, MAX_FILE_BYTES)
            require(sha256(content) == expected, "FROZEN_MODEL_BYTES_DRIFT")
            if file == "metadata.json":
                metadata[name] = read_json(content.decode())
    v1, v2 = metadata["v1"], metadata["v2"]
    require(
        sha256(encode(v1["support"])) == config["evaluation"]["support_profile_sha256"]
        and v1["training"]["source"]["train_fingerprint"]
        == config["evaluation"]["training_fingerprint"]
        and all(m["feature_order"] == config["contract"]["feature_columns"] for m in (v1, v2))
        and all(m["target"] == config["contract"]["target"] for m in (v1, v2))
        and all(m["promotion_decision"] == "NO_ML_PROMOTION" for m in (v1, v2))
        and all(v1["models"][m["name"]]["identity"] == m["identity"] for m in config["models"][:3]),
        "FROZEN_MODEL_CONTRACT_DRIFT",
    )
    return metadata


def load_frozen_models() -> FrozenModels:
    """Fixed production locations and receipts only; never accepts caller model paths."""
    config = load_protocol()
    verify_frozen_sources(config)
    checked = verify_model_receipts(config)
    from loometric.experimental_ml.artifacts import load_trusted
    from loometric.experimental_ml_v2.artifacts import load_trusted_offline

    # Existing loaders reverify their exact in-memory buffers before joblib.load,
    # including environment, pipeline types and frozen research source identity.
    v1, models = load_trusted(config["frozen_bundles"]["v1"]["manifest_sha256"])
    v2, candidate = load_trusted_offline()
    require(v1 == checked["v1"] and v2 == checked["v2"], "FROZEN_MODEL_METADATA_RACE")
    models["rf_physics"] = candidate
    require(set(models) == {m["name"] for m in config["models"]}, "FOUR_FROZEN_MODELS_REQUIRED")
    return FrozenModels(models, v1["support"], config["frozen_bundles"])
