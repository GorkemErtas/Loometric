"""Verify candidate predictions against retained EXP-008 results."""

import json

import numpy as np
from threadpoolctl import threadpool_limits

from loometric.experimental_ml_v2.artifacts import (
    load_trusted_offline,
)
from loometric.experimental_ml_v2.constants import (
    ROOT,
    SOURCE_DIRECTORY,
    SOURCE_MANIFEST_SHA256,
)
from loometric.ml_research.artifacts import inspect_research
from loometric.synthetic_training.data import load_development


def verify_parity() -> dict:
    inspect_research(
        SOURCE_DIRECTORY,
        SOURCE_MANIFEST_SHA256,
    )

    _, model = load_trusted_offline()

    config = json.loads((ROOT / "configs/synthetic_training_v1.json").read_text(encoding="utf-8"))

    case = "benchmark-42-baseline"

    binding = next(item for item in config["datasets"] if item["case_id"] == case)

    data = load_development(
        ROOT / binding["directory"],
        expected_fingerprint=(binding["expected_manifest_fingerprint"]),
    )

    rows = [
        json.loads(line)
        for line in (SOURCE_DIRECTORY / "spent-diagnostics.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    retained = [row for row in rows if row["case"] == case and row["model"] == "rf_physics"]

    expected = {row["observation_id"]: row["prediction"] for row in retained}

    X = data.validation.X
    y = data.validation.y.to_numpy(dtype=float)

    if len(retained) != len(X) or len(expected) != len(X) or set(expected) != set(X.index):
        raise ValueError("Validation row mismatch.")

    with threadpool_limits(limits=1):
        predicted = np.asarray(model.predict(X), dtype=float)

    reference = np.asarray(
        [expected[oid] for oid in X.index],
        dtype=float,
    )

    if not np.isfinite(predicted).all():
        raise ValueError("Non-finite predictions.")

    max_difference = float(np.max(np.abs(predicted - reference)))

    if max_difference > 1e-12:
        raise ValueError("Prediction parity failed.")

    errors = predicted - y

    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))

    r2 = float(1 - np.sum(errors**2) / np.sum((y - np.mean(y)) ** 2))

    return {
        "status": "PARITY_VERIFIED",
        "model": "rf_physics",
        "case": case,
        "validation_rows": len(X),
        "maximum_absolute_difference": max_difference,
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "fresh_validation": False,
        "promotion_decision": "NO_ML_PROMOTION",
    }


if __name__ == "__main__":
    print(json.dumps(verify_parity(), indent=2))
