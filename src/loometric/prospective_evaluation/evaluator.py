"""Create-only two-pass evaluator: all frozen predictions sealed before any target read."""

from fractions import Fraction
from pathlib import Path

import pandas as pd

from loometric.prediction.contracts import read_json
from loometric.prospective_evaluation.acceptance import evaluate_acceptance
from loometric.prospective_evaluation.diagnostics import (
    case_diagnostics,
    comparisons,
    date_sensitivity,
)
from loometric.prospective_evaluation.evaluation_access import read_validation_labels, verify_seal
from loometric.prospective_evaluation.protocol import (
    PROTOCOL_SHA256,
    load_protocol,
    verify_frozen_sources,
)
from loometric.prospective_evaluation.receipts import _verify_ledger
from loometric.prospective_evaluation.source import audit_source, expected_source, require
from loometric.prospective_evaluation.storage import (
    MAX_FILE_BYTES,
    MAX_MANIFEST_BYTES,
    encode,
    environment,
    identity,
    read_checked,
    require_sha,
    root_size,
    safe_path,
    sha256,
    write_new,
)
from loometric.synthetic_ml.features import FEATURE_COLUMNS
from loometric.synthetic_training.data import CATEGORICAL, exact_float
from loometric.synthetic_training.risk import assess_support

PAYLOAD_FILES = {
    "attempt.json",
    "predictions.jsonl",
    "predictions.receipt.json",
    "errors.jsonl",
    "report.json",
}


def evaluation_identity() -> dict:
    directory = Path(__file__).parent
    return {
        **{p.name: sha256(p.read_bytes()) for p in sorted(directory.glob("*.py"))},
        "../execution.py": sha256((directory.parent / "execution.py").read_bytes()),
    }


def _admit_run(root: Path, run: str, expected_a: str | None) -> tuple[str, dict | None]:
    require(run in ("a", "b"), "TWO_DECLARED_RUNS_ONLY")
    runs = safe_path(root, "runs")
    require(
        not runs.exists() or {p.name for p in runs.iterdir()} <= {"a", "b"},
        "CLOSED_RUN_DIRECTORIES_REQUIRED",
    )
    prefix = f"runs/{run}"
    require(not safe_path(root, prefix).exists(), "CREATE_ONLY_RUN_REQUIRED")
    previous = None
    if run == "a":
        require(
            expected_a is None and not safe_path(root, "runs/b").exists(), "ORIGINAL_RUN_REQUIRED"
        )
    else:
        require_sha(expected_a)
        previous = inspect_run(root, "a", expected_a)
        require(
            previous["state"] == "SEALED_PENDING_REPRODUCTION", "COMPLETE_ORIGINAL_RUN_REQUIRED"
        )
    safe_path(root, prefix).mkdir(parents=True, exist_ok=False)
    return prefix, previous


def inspect_run(root: Path, run: str, expected_sha: str) -> dict:
    require(run in ("a", "b"), "TWO_DECLARED_RUNS_ONLY")
    require_sha(expected_sha)
    prefix = f"runs/{run}"
    directory = safe_path(root, prefix)
    require(
        {p.name for p in directory.iterdir()} == PAYLOAD_FILES | {"manifest.json"},
        "CLOSED_COMPLETED_RUN_REQUIRED",
    )
    raw = read_checked(directory / "manifest.json", MAX_MANIFEST_BYTES)
    require(sha256(raw) == expected_sha, "INDEPENDENT_RUN_RECEIPT_DRIFT")
    manifest = read_json(raw.decode())
    require(
        set(manifest)
        == {
            "protocol_sha256",
            "ledger_sha256",
            "evaluation_code",
            "environment",
            "promotion_decision",
            "files",
            "state",
            "original_manifest_sha256",
            "decision",
        },
        "CLOSED_RUN_MANIFEST_REQUIRED",
    )
    require(set(manifest["files"]) == PAYLOAD_FILES, "CLOSED_RUN_MANIFEST_REQUIRED")
    for name, expected in manifest["files"].items():
        require(
            identity(read_checked(directory / name, MAX_FILE_BYTES)) == expected,
            "RUN_FILE_INTEGRITY_DRIFT",
        )
    require(manifest["promotion_decision"] == "NO_ML_PROMOTION", "RUN_PROMOTION_POLICY_DRIFT")
    return manifest


def verify_reproduction(root: Path, expected_a: str, expected_b: str, ledger_sha: str) -> dict:
    """Independent read-only inspection of both closed runs and actual payload bytes."""
    a, b = inspect_run(root, "a", expected_a), inspect_run(root, "b", expected_b)
    require(
        all(
            m["protocol_sha256"] == PROTOCOL_SHA256
            and m["ledger_sha256"] == ledger_sha
            and m["evaluation_code"] == evaluation_identity()
            and m["environment"] == environment()
            for m in (a, b)
        ),
        "REPRODUCTION_IDENTITY_DRIFT",
    )
    require(
        b["state"] == "REPRODUCTION_VERIFIED" and b["original_manifest_sha256"] == expected_a,
        "REPRODUCTION_ORIGINAL_BINDING_DRIFT",
    )
    require(a["files"] == b["files"], "DETERMINISTIC_EVALUATION_REPRODUCTION_FAILED")
    for name in PAYLOAD_FILES:
        require(
            read_checked(safe_path(root, f"runs/a/{name}"), MAX_FILE_BYTES)
            == read_checked(safe_path(root, f"runs/b/{name}"), MAX_FILE_BYTES),
            "DETERMINISTIC_EVALUATION_REPRODUCTION_FAILED",
        )
    return {
        "status": "REPRODUCTION_VERIFIED",
        "decision": b["decision"],
        "promotion_decision": "NO_ML_PROMOTION",
    }


def feature_observations(design, source):
    features = {r["observation_id"]: r for r in audit_source(source, design)}
    plans = {p.observation_id: p for p in source.plans}
    shifts = {s.shift_id: s for s in source.shifts}
    observations = []
    for member in source.membership:
        if member.partition != "validation":
            continue
        feature, plan = features[member.observation_id], plans[member.observation_id]
        raw = feature["inputs"]
        inputs = {
            c: str(raw[c]) if c in CATEGORICAL else exact_float(raw[c]) for c in FEATURE_COLUMNS
        }
        capacity = raw["planned_workers"] * raw["available_minutes"]
        date = shifts[plan.shift_id].start.date()
        observations.append(
            {
                "id": f"{design.case.world_id}::{member.observation_id}",
                "local_id": member.observation_id,
                "world_id": design.case.world_id,
                "case_id": design.case.case_id,
                "inputs": inputs,
                "defined_target": capacity > 0,
                "date": date.isoformat(),
                "calendar_week": f"{date.isocalendar().year}-W{date.isocalendar().week:02d}",
                "stage": inputs["stage"],
                "shift_kind": inputs["shift_kind"],
                **{
                    name: f"{design.case.world_id}::{feature['context'][name + '_id']}"
                    for name in ("factory", "line", "crew", "style")
                },
                "offered_ceiling": str(
                    Fraction(raw["order_quantity"])
                    * Fraction(raw["standard_worker_minutes_per_piece"])
                    / capacity
                )
                if capacity
                else None,
            }
        )
    require(len(observations) == design.case.planned_rows, "PLANNED_SCORE_POPULATION_DRIFT")
    return observations


def _infer_case(observations, frozen, counters, budget):
    defined = [r for r in observations if r["defined_target"]]
    require(
        counters["predictions"] + len(defined) * 4 <= budget["maximum_scored_predictions_per_run"],
        "PREDICTION_COUNT_BUDGET",
    )
    frame = pd.DataFrame([r["inputs"] for r in defined], columns=FEATURE_COLUMNS)
    predictions = {}
    import numpy as np

    for model, estimator in frozen.models.items():
        if defined:
            require(
                counters["calls"] < budget["maximum_raw_model_predict_calls_per_run"],
                "PREDICT_CALL_BUDGET",
            )
            counters["calls"] += 1
            values = np.asarray(estimator.predict(frame), dtype=float)
            require(
                values.shape == (len(defined),) and np.isfinite(values).all(),
                "NONFINITE_OR_MALFORMED_PREDICTIONS",
            )
        else:
            values = []
        predictions[model] = dict(zip((r["id"] for r in defined), map(float, values), strict=True))
    counters["predictions"] += len(defined) * 4
    for row in observations:
        row["input_support"] = assess_support(row["inputs"], frozen.profile)
        row["predictions"] = {m: predictions[m].get(row["id"]) for m in frozen.models}
        row["support"] = {
            m: assess_support(row["inputs"], frozen.profile, row["predictions"][m])
            for m in frozen.models
        }


def _matched_predictions(cases, designs, tolerance):
    for offset in range(0, 8, 2):
        left, right = (cases[d.case.case_id] for d in designs[offset : offset + 2])
        require(len(left) == len(right), "PAIRED_PREDICTION_POPULATION_DRIFT")
        for a, b in zip(left, right, strict=True):
            require(
                a["id"] == b["id"]
                and a["inputs"] == b["inputs"]
                and a["defined_target"] == b["defined_target"],
                "PAIRED_INPUT_DRIFT",
            )
            for model, prediction in a["predictions"].items():
                other = b["predictions"][model]
                require(
                    other is None
                    if prediction is None
                    else other is not None and abs(prediction - other) <= tolerance,
                    "PAIRED_FROZEN_PREDICTION_DRIFT",
                )


def _evaluate(
    root,
    designs,
    history,
    ledger_sha,
    frozen_loader,
    *,
    run="a",
    expected_a=None,
    final_integrity_check=None,
):
    """Private mechanical seam. The public worker supplies ONLY frozen declared designs."""
    config = load_protocol()
    prefix, previous = _admit_run(root, run, expected_a)
    binding = {
        "protocol_sha256": PROTOCOL_SHA256,
        "ledger_sha256": ledger_sha,
        "evaluation_code": evaluation_identity(),
        "environment": environment(),
        "promotion_decision": "NO_ML_PROMOTION",
    }
    write_new(root, f"{prefix}/attempt.json", encode(binding))
    _verify_ledger(root, designs, ledger_sha, history)
    ledger_bytes = read_checked(safe_path(root, "receipts/datasets.json"), MAX_MANIFEST_BYTES)
    require(sha256(ledger_bytes) == ledger_sha, "INDEPENDENT_LEDGER_RECEIPT_DRIFT")
    ledger = read_json(ledger_bytes.decode())
    frozen = frozen_loader()
    names = [m["name"] for m in config["models"]]
    require(set(frozen.models) == set(names), "FOUR_FROZEN_MODELS_REQUIRED")
    cases, sources = {}, {}
    counters = {"calls": 0, "predictions": 0}
    for design in designs:
        source = expected_source(design.configuration)
        sources[design.case.case_id] = source
        rows = feature_observations(design, source)
        _infer_case(rows, frozen, counters, config["budget"])
        cases[design.case.case_id] = rows
    _matched_predictions(
        cases, designs, config["evaluation"]["paired_prediction_absolute_tolerance"]
    )
    predictions = b"".join(encode(r) for d in designs for r in cases[d.case.case_id])
    write_new(root, f"{prefix}/predictions.jsonl", predictions)
    seal = {
        **binding,
        "models": frozen.receipts,
        "counts": counters,
        "predictions": identity(predictions),
        "state": "ALL_EIGHT_CASES_PREDICTED_BEFORE_VALIDATION_LABELS",
    }
    seal_bytes = encode(seal)
    write_new(root, f"{prefix}/predictions.receipt.json", seal_bytes)
    seal_sha = sha256(seal_bytes)
    if previous is not None:
        require(
            previous["files"]["predictions.jsonl"] == identity(predictions)
            and previous["files"]["predictions.receipt.json"] == identity(seal_bytes),
            "REPRODUCTION_PREDICTION_DRIFT_BEFORE_LABELS",
        )

    def seal_check():
        return verify_seal(root, prefix, seal_sha, seal)

    # Read back the exact sealed vectors, not mutable estimator output objects.
    sealed_rows = seal_check()
    cases = {d.case.case_id: [] for d in designs}
    for row in sealed_rows:
        cases[row["case_id"]].append(row)
    for design in designs:
        labels = read_validation_labels(
            root,
            design,
            sources[design.case.case_id],
            seal_check,
            expected_manifest_sha=ledger["datasets"][design.case.case_id]["manifest_sha256"],
        )
        for row in cases[design.case.case_id]:
            target = labels[row["local_id"]]
            require(
                row["defined_target"] == (target is not None), "DEFINED_TARGET_POPULATION_DRIFT"
            )
            row["actual"] = exact_float(target) if target is not None else None
    errors = b"".join(
        encode(
            {
                "id": r["id"],
                "case_id": d.case.case_id,
                "actual": r["actual"],
                "exclusion_reason": None
                if r["actual"] is not None
                else "ZERO_PLANNED_CAPACITY_UNDEFINED_TARGET",
                "signed_errors": {
                    m: r["predictions"][m] - r["actual"] if r["actual"] is not None else None
                    for m in names
                },
            }
        )
        for d in designs
        for r in cases[d.case.case_id]
    )
    write_new(root, f"{prefix}/errors.jsonl", errors)
    diagnostics = {
        d.case.case_id: case_diagnostics(cases[d.case.case_id], names, config) for d in designs
    }
    compared = comparisons(cases, designs, names)
    sensitivity = date_sensitivity(cases, designs, names, config)
    acceptance = evaluate_acceptance(diagnostics, designs, compared, config)
    report = {
        **binding,
        "schema_version": 1,
        "experiment_id": "EXP-009",
        "diagnostics": diagnostics,
        "comparisons": compared,
        "date_sensitivity": sensitivity,
        "acceptance": acceptance,
        "prediction_seal_sha256": seal_sha,
        "resource_counts": counters,
        "validity": {
            "ledger_verified_before_inference": True,
            "whole_pass_sealed_before_labels": True,
            "reserved_labels_decoded": False,
            "fits": 0,
            "hyperparameter_trials": 0,
            "calibration_fits": 0,
        },
        "uncertainty_interpretation": config["uncertainty"]["interpretation"],
    }
    seal_check()
    _verify_ledger(
        root, designs, ledger_sha, history
    )  # Detect dataset/receipt changes across scoring.
    require(
        evaluation_identity() == binding["evaluation_code"]
        and environment() == binding["environment"],
        "EVALUATION_IDENTITY_DRIFT",
    )
    verify_frozen_sources(config)
    if final_integrity_check is not None:
        final_integrity_check()
    write_new(root, f"{prefix}/report.json", encode(report))
    files = {
        n: identity(read_checked(safe_path(root, f"{prefix}/{n}"), MAX_FILE_BYTES))
        for n in sorted(PAYLOAD_FILES)
    }
    if previous is not None:
        require(previous["files"] == files, "DETERMINISTIC_EVALUATION_REPRODUCTION_FAILED")
        for name in PAYLOAD_FILES:
            require(
                read_checked(safe_path(root, f"runs/a/{name}"), MAX_FILE_BYTES)
                == read_checked(safe_path(root, f"runs/b/{name}"), MAX_FILE_BYTES),
                "DETERMINISTIC_EVALUATION_REPRODUCTION_FAILED",
            )
    manifest = {
        **binding,
        "files": files,
        "state": "REPRODUCTION_VERIFIED" if previous else "SEALED_PENDING_REPRODUCTION",
        "original_manifest_sha256": expected_a,
        "decision": acceptance["provisional_status"] if previous else "PENDING_REPRODUCTION",
    }
    raw = encode(manifest)
    write_new(
        root, f"{prefix}/manifest.json", raw
    )  # Completion marker last; failures remain incomplete.
    root_size(root)
    return {
        "status": manifest["state"],
        "manifest_sha256": sha256(raw),
        "decision": manifest["decision"],
        "promotion_decision": "NO_ML_PROMOTION",
    }
