"""Read trusted-local M01 metadata and hash bytes, without deserialization or inference."""

import hashlib
from datetime import date
from pathlib import Path

from loometric.compatibility.contracts import ModelProfile, bounded_json, require_digest


def inspect_model_profile(directory: Path, *, expected_fingerprint: str) -> ModelProfile:
    """The expected digest must come from an independently retained M01 receipt.

    Checksums do not authenticate a publisher. This verifies metadata/byte integrity,
    not serialized estimator behavior; it deliberately never calls joblib.load.
    """
    from loometric.prediction.artifacts import digest, environment, model_configuration

    require_digest(expected_fingerprint)
    try:
        with (directory / "manifest.json").open("rb") as source:
            content = source.read(262145)
        bounded_json(content.decode("utf-8"))
        # M01 hashes JSON's finite machine floats, not planning Decimal strings.
        from loometric.prediction.contracts import read_json

        manifest = read_json(content.decode("utf-8"))
        if digest(manifest) != expected_fingerprint:
            raise ValueError("M01 manifest fingerprint differs from the retained receipt.")
        if any(
            type(manifest[name]) is not int or manifest[name] != 1
            for name in ("artifact_schema_version", "input_schema_version")
        ):
            raise ValueError("Unsupported M01 artifact schema.")
        configuration = model_configuration()
        if (
            manifest["configuration"] != configuration
            or manifest["model_configuration_fingerprint"] != digest(configuration)
            or manifest["environment"] != environment()
        ):
            raise ValueError("M01 configuration or environment does not match the frozen artifact.")
        lineage = dict(manifest["lineage"])
        claimed = lineage.pop("training_split_fingerprint")
        if digest(lineage) != claimed:
            raise ValueError("M01 training lineage fingerprint differs.")
        hasher = hashlib.sha256()
        with (directory / "pipeline.joblib").open("rb") as source:
            if source.seek(0, 2) > 16 * 1024 * 1024:
                raise ValueError("M01 artifact exceeds the offline inspection byte limit.")
            source.seek(0)
            for block in iter(lambda: source.read(65536), b""):
                hasher.update(block)
        if hasher.hexdigest() != manifest["pipeline_sha256"]:
            raise ValueError("M01 pipeline byte fingerprint differs.")
        categories = manifest["training_categories"]
        return ModelProfile(
            expected_fingerprint,
            manifest["model_configuration_fingerprint"],
            lineage["dataset_sha256"],
            lineage["split_file_sha256"],
            manifest["pipeline_sha256"],
            date.fromisoformat(lineage["training"]["end"]),
            tuple(categories["department"]),
            tuple(categories["team"]),
            tuple(categories["day_of_week"]),
            configuration["model_id"],
            configuration["model_version"],
        )
    except (KeyError, TypeError, UnicodeError, OverflowError) as exc:
        raise ValueError("Malformed M01 metadata; no model was loaded.") from exc
