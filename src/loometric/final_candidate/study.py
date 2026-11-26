"""One fit, immutable candidate, then one held-out pass and one byte reproduction."""

import io
from datetime import datetime
from itertools import combinations
from math import fsum

import joblib
import numpy as np
import pandas as pd

from loometric.final_candidate import data
from loometric.final_candidate.history import HISTORY_COLUMNS
from loometric.final_candidate.model import MODEL_COLUMNS, HistoryBoost
from loometric.prospective_evaluation.diagnostics import METRICS, bootstrap_interval, metrics
from loometric.prospective_evaluation.frozen_models import load_frozen_models
from loometric.prospective_evaluation.source import require
from loometric.prospective_evaluation.storage import (
    encode,
    environment,
    read_checked,
    root_size,
    sha256,
    write_new,
)
from loometric.synthetic_ml.features import FEATURE_COLUMNS
from loometric.synthetic_training.risk import assess_support

NAMES = (
    "grouped_mean",
    "random_forest",
    "histogram_gradient_boosting",
    "rf_physics",
    "history_boost",
    "missing_history_control",
)


def frame(rows: list[dict], missing: bool = False) -> pd.DataFrame:
    values = []
    for row in rows:
        history = (
            row["history"]
            if not missing
            else {k: 0 if k.endswith("count") else None for k in HISTORY_COLUMNS}
        )
        values.append({**row["inputs"], **history})
    return pd.DataFrame(values, columns=MODEL_COLUMNS)


def mean_metrics(cells: list[dict]) -> dict:
    return {
        m: fsum(v[m] for v in cells) / len(cells) if all(v[m] is not None for v in cells) else None
        for m in METRICS
    }


def source_rows(group: str, receipts: dict, partition: str) -> dict:
    seeds = data.config()["heldout_seeds" if group == "heldout" else "development_seeds"]
    require(
        set(receipts)
        == {f"{seed}-{condition}" for seed in seeds for condition in ("baseline", "disruption")},
        "EIGHT_DECLARED_SOURCE_RECEIPTS_REQUIRED",
    )
    result = {}
    for case, receipt in sorted(receipts.items()):
        rows, _ = data.read_case(data.DIRECTORY, group, case, receipt)
        selected = [r for r in rows if r["split"] == partition]
        require(bool(selected), "EMPTY_DECLARED_SCORE_POPULATION")
        result[case] = selected
    return result


def load_candidate(expected: str):
    raw = read_checked(data.DIRECTORY / "candidate.joblib", 32 * 1024**2)
    require(sha256(raw) == expected, "FROZEN_CANDIDATE_BYTES_DRIFT")
    model = joblib.load(io.BytesIO(raw))
    require(
        isinstance(model, HistoryBoost)
        and model.parameters == data.config()["estimator"]
        and model.configuration_sha256 == sha256(encode(data.config()))
        and model.code_identity == data.core_identity(),
        "FROZEN_CANDIDATE_TYPE_DRIFT",
    )
    return model


def develop() -> dict:
    c = data.config()
    require(not data.DIRECTORY.exists(), "CREATE_ONLY_EXPERIMENT_REQUIRED")
    write_new(
        data.DIRECTORY,
        "attempt.json",
        encode({"configuration_sha256": sha256(encode(c)), "code": data.core_identity()}),
    )
    receipts = data.prepare(False)
    rows = []
    for case, receipt in sorted(receipts.items()):
        features, _ = data.read_case(data.DIRECTORY, "development", case, receipt)
        labels = data.read_labels(
            data.DIRECTORY, "development", case, "fit", expected_manifest_sha=receipt
        )
        for row in features:
            if row["split"] == "fit" and row["defined_target"]:
                require(
                    row["id"] in labels and labels[row["id"]]["actual"] is not None,
                    "FIT_JOIN_DRIFT",
                )
                rows.append({**row, "actual": labels[row["id"]]["actual"]})
    require(0 < len(rows) <= c["budget"]["maximum_training_rows"], "TRAINING_ROW_BUDGET")
    check = source_rows("development", receipts, "development")
    require(
        max(datetime.fromisoformat(r["label_available_at"]) for r in rows)
        < min(datetime.fromisoformat(r["cutoff"]) for v in check.values() for r in v),
        "GLOBAL_TRAINING_MATURITY_FAILED",
    )
    frozen = load_frozen_models()
    model = HistoryBoost(frozen.models["rf_physics"], c["estimator"])
    model.fit(frame(rows), pd.Series([r["actual"] for r in rows]))
    model.configuration_sha256 = sha256(encode(c))
    model.code_identity = data.core_identity()
    stream = io.BytesIO()
    joblib.dump(model, stream, compress=3)
    model_bytes = stream.getvalue()
    write_new(data.DIRECTORY, "candidate.joblib", model_bytes)
    receipt = {
        "model_sha256": sha256(model_bytes),
        "configuration_sha256": sha256(encode(c)),
        "code": data.core_identity(),
        "environment": environment(),
        "estimator_fits": 1,
        "fit_rows": len(rows),
        "fit_seeds": c["development_seeds"],
        "fit_fingerprint": sha256(encode(rows)),
        "first_date": min(r["date"] for r in rows),
        "last_date": max(r["date"] for r in rows),
        "sources": receipts,
        "promotion_decision": "NO_ML_PROMOTION",
    }
    write_new(data.DIRECTORY, "candidate.receipt.json", encode(receipt))
    # No fitting or parameter choice is made from this development check.
    diagnostics = evaluate_rows(check, model, frozen, "development", "development/check", receipts)
    write_new(data.DIRECTORY, "development/report.json", encode(diagnostics))
    require(root_size(data.DIRECTORY) <= 256 * 1024**2, "OUTPUT_ROOT_LIMIT")
    return {
        "status": "ONE_FIT_FROZEN_BEFORE_HELDOUT",
        "candidate": receipt,
        "development": diagnostics["macro"],
    }


def evaluate_rows(cases, model, frozen, group: str, prefix: str, receipts: dict) -> dict:
    predicted = {}
    calls = 0
    for case, planned in cases.items():
        rows = [dict(r) for r in planned if r["defined_target"]]
        X = frame(rows)
        raw = X.loc[:, FEATURE_COLUMNS]
        predictions = {}
        for name, estimator in frozen.models.items():
            predictions[name] = np.asarray(estimator.predict(raw), dtype=float)
            calls += 1
        predictions["history_boost"] = model.predict(X)
        calls += 1
        predictions["missing_history_control"] = model.predict(frame(rows, True))
        calls += 1
        require(
            all(v.shape == (len(rows),) and np.isfinite(v).all() for v in predictions.values()),
            "FINITE_ALIGNED_PREDICTIONS_REQUIRED",
        )
        for i, row in enumerate(rows):
            row["predictions"] = {name: float(values[i]) for name, values in predictions.items()}
            row["input_support"] = assess_support(row["inputs"], frozen.profile)
        predicted[case] = rows
    require(calls <= 48, "PREDICT_CALL_BUDGET")
    content = b"".join(
        encode({"case": case, **row}) for case, rows in predicted.items() for row in rows
    )
    write_new(data.DIRECTORY, prefix + ".predictions.jsonl", content)
    prediction_sha = sha256(content)
    write_new(
        data.DIRECTORY,
        prefix + ".seal.json",
        encode(
            {"sha256": prediction_sha, "rows": sum(map(len, predicted.values())), "calls": calls}
        ),
    )
    require(
        sha256(read_checked(data.DIRECTORY / (prefix + ".predictions.jsonl"), 32 * 1024**2))
        == prediction_sha,
        "PREDICTION_SEAL_DRIFT",
    )
    token = data.evaluation_labels_enabled.set(True)
    try:
        cells = {}
        for case, rows in predicted.items():
            labels = data.read_labels(
                data.DIRECTORY,
                group,
                case,
                "evaluation" if group == "heldout" else "development",
                expected_manifest_sha=receipts[case],
            )
            require(set(labels) == {r["id"] for r in cases[case]}, "EXACT_SCORE_LABEL_IDS_REQUIRED")
            require(
                all(
                    r["defined_target"] == (labels[r["id"]]["actual"] is not None)
                    for r in cases[case]
                ),
                "TARGET_ELIGIBILITY_DRIFT",
            )
            for row in rows:
                require(labels[row["id"]]["actual"] is not None, "DEFINED_TARGET_JOIN_DRIFT")
                row["actual"] = labels[row["id"]]["actual"]
            cells[case] = {
                "planned_rows": len(cases[case]),
                "defined_targets": len(rows),
                "excluded_zero_capacity": len(cases[case]) - len(rows),
                "history_available": sum(
                    r["history"]["recent_attainment_mean"] is not None for r in rows
                ),
                "input_status_counts": {
                    s: sum(r["input_support"]["status"] == s for r in rows)
                    for s in ("SUPPORTED_EXPERIMENTAL", "REVIEW_REQUIRED", "ABSTAIN")
                },
                "models": {
                    name: {
                        "metrics": metrics(rows, name),
                        "stages": {
                            stage: metrics([r for r in rows if r["inputs"]["stage"] == stage], name)
                            for stage in sorted({r["inputs"]["stage"] for r in rows})
                        },
                        "above_offered_work": sum(
                            r["predictions"][name]
                            > r["inputs"]["order_quantity"]
                            * r["inputs"]["standard_worker_minutes_per_piece"]
                            / (r["inputs"]["available_minutes"] * r["inputs"]["planned_workers"])
                            + 1e-12
                            for r in rows
                        ),
                        "support_status_counts": {
                            status: sum(
                                candidate_support(r, model, frozen.profile, name)["status"]
                                == status
                                for r in rows
                            )
                            for status in ("SUPPORTED_EXPERIMENTAL", "REVIEW_REQUIRED", "ABSTAIN")
                        },
                    }
                    for name in NAMES
                },
            }
    finally:
        data.evaluation_labels_enabled.reset(token)
    macro = {
        condition: {
            name: mean_metrics(
                [v["models"][name]["metrics"] for k, v in cells.items() if k.endswith(condition)]
            )
            for name in NAMES
        }
        for condition in ("baseline", "disruption")
    }
    compared = {
        condition: {
            a + "_minus_" + b: bootstrap_interval(
                [
                    cells[f"{seed}-{condition}"]["models"][a]["metrics"]["mae"]
                    - cells[f"{seed}-{condition}"]["models"][b]["metrics"]["mae"]
                    for seed in data.config()[
                        "heldout_seeds" if group == "heldout" else "development_seeds"
                    ]
                ]
            )
            for a, b in combinations(NAMES, 2)
        }
        for condition in ("baseline", "disruption")
    }
    for case, receipt in receipts.items():
        data.read_case(data.DIRECTORY, group, case, receipt)
    require(
        sha256(read_checked(data.DIRECTORY / (prefix + ".predictions.jsonl"), 32 * 1024**2))
        == prediction_sha,
        "PREDICTION_SEAL_DRIFT",
    )
    return {
        "cases": cells,
        "macro": macro,
        "world_bootstrap": compared,
        "prediction_sha256": prediction_sha,
        "calls": calls,
        "promotion_decision": "NO_ML_PROMOTION",
    }


def candidate_support(row, model, legacy_profile, name):
    is_candidate = name in ("history_boost", "missing_history_control")
    result = assess_support(
        row["inputs"],
        model.input_profile if is_candidate else legacy_profile,
        row["predictions"][name],
    )
    if is_candidate and result["status"] != "ABSTAIN":
        history = row["history"]
        if (
            name == "missing_history_control"
            or history["recent_attainment_mean"] is None
            or history["history_age_hours"] is None
            or history["history_age_hours"] > 72
        ):
            result = {
                "status": "REVIEW_REQUIRED",
                "reason_codes": ["MISSING_OR_STALE_MATURE_HISTORY"],
            }
    return result


def integration_guards(report: dict) -> dict:
    checks = {}
    threshold = data.config()["acceptance"]

    def bound(key, candidate, reference, percent):
        checks[key] = {
            "passed": candidate <= reference * (1 + percent / 100),
            "candidate": candidate,
            "reference": reference,
            "maximum_regression_percent": percent,
        }

    for condition, values in report["macro"].items():
        candidate = values["history_boost"]
        for reference in ("random_forest", "rf_physics"):
            bound(
                condition + "|mae_gain|" + reference,
                candidate["mae"],
                values[reference]["mae"],
                -threshold["minimum_mae_gain_vs_forest_and_physics_percent_each_condition"],
            )
        bound(
            condition + "|history_contribution",
            candidate["mae"],
            values["missing_history_control"]["mae"],
            -2,
        )
        for metric in ("rmse", "p95_absolute_error"):
            bound(condition + "|" + metric, candidate[metric], values["rf_physics"][metric], 0)
        selected = [v for k, v in report["cases"].items() if k.endswith(condition)]
        bound(
            condition + "|worst",
            max(v["models"]["history_boost"]["metrics"]["worst_absolute_error"] for v in selected),
            max(v["models"]["rf_physics"]["metrics"]["worst_absolute_error"] for v in selected),
            10,
        )
        wins = sum(
            v["models"]["history_boost"]["metrics"]["mae"]
            < v["models"]["rf_physics"]["metrics"]["mae"]
            for v in selected
        )
        checks[condition + "|wins"] = {"passed": wins >= 3, "wins": wins}
        for stage in selected[0]["models"]["history_boost"]["stages"]:
            averages = {
                name: fsum(v["models"][name]["stages"][stage]["mae"] for v in selected) / 4
                for name in ("history_boost", "rf_physics", "random_forest")
            }
            bound(
                condition + "|stage|" + stage,
                averages["history_boost"],
                min(averages["rf_physics"], averages["random_forest"]),
                10,
            )
    for case, v in report["cases"].items():
        checks[case + "|count"] = {
            "passed": v["defined_targets"] >= 300,
            "rows": v["defined_targets"],
        }
        bound(
            case + "|world",
            v["models"]["history_boost"]["metrics"]["mae"],
            v["models"]["rf_physics"]["metrics"]["mae"],
            10,
        )
    # Stored pair direction is physics minus candidate; reverse its interval.
    interval = report["world_bootstrap"]["baseline"]["rf_physics_minus_history_boost"]["interval"]
    checks["primary_interval"] = {
        "passed": -interval[0] < 0,
        "candidate_minus_physics_interval": [-interval[1], -interval[0]],
    }
    return {
        "eligible_for_experimental_integration": all(v["passed"] for v in checks.values()),
        "guards": checks,
        "promotion_decision": "NO_ML_PROMOTION",
    }


def evaluate(
    expected_model: str,
    *,
    reproduce: bool = False,
    source_receipts: dict | None = None,
    expected_report: str | None = None,
) -> dict:
    c = data.config()
    name = "b" if reproduce else "a"
    prefix = "heldout/" + name
    require(
        not (data.DIRECTORY / (prefix + ".report.json")).exists()
        and not (data.DIRECTORY / (prefix + ".attempt.json")).exists(),
        "CREATE_ONLY_EVALUATION_REQUIRED",
    )
    if not reproduce:
        require(source_receipts is None, "NO_CALLER_SELECTED_HELDOUT_SOURCES")
        # Verify the externally retained candidate receipt before generating unseen outcomes.
        model = load_candidate(expected_model)
        source_receipts = data.prepare(True)
        write_new(data.DIRECTORY, "heldout/receipts.json", encode(source_receipts))
    else:
        require(
            source_receipts is not None and expected_report is not None,
            "INDEPENDENT_REPRODUCTION_RECEIPTS_REQUIRED",
        )
        model = load_candidate(expected_model)
    write_new(
        data.DIRECTORY,
        prefix + ".attempt.json",
        encode(
            {
                "candidate_sha256": expected_model,
                "configuration_sha256": sha256(encode(c)),
                "source_receipts": source_receipts,
            }
        ),
    )
    cases = source_rows("heldout", source_receipts, "evaluation")
    frozen = load_frozen_models()
    report = evaluate_rows(cases, model, frozen, "heldout", prefix, source_receipts)
    report["integration"] = integration_guards(report)
    report["candidate_sha256"] = expected_model
    report["source_receipts"] = source_receipts
    content = encode(report)
    if reproduce:
        original = read_checked(data.DIRECTORY / "heldout/a.report.json", 32 * 1024**2)
        require(
            sha256(original) == expected_report and original == content,
            "REPORT_REPRODUCTION_FAILED",
        )
    write_new(data.DIRECTORY, prefix + ".report.json", content)
    require(root_size(data.DIRECTORY) <= 256 * 1024**2, "OUTPUT_ROOT_LIMIT")
    return {
        "status": "REPRODUCED" if reproduce else "FROZEN_HELDOUT_SCORED",
        "report_sha256": sha256(content),
        "source_receipts": source_receipts,
        "integration": report["integration"],
        "macro": report["macro"],
        "promotion_decision": "NO_ML_PROMOTION",
    }
