import copy
import json
from pathlib import Path

import pytest

from loometric.synthetic_training.configuration import BASELINES, load_study
from loometric.synthetic_training.selection import select_model, training_choices


@pytest.fixture
def evidence():
    config = load_study(Path(__file__).resolve().parents[2] / "configs/synthetic_training_v1.json")
    worlds = [
        "development-19-baseline",
        "development-42-baseline",
        "development-73-baseline",
        "benchmark-42-baseline",
    ]
    means = {
        "global_mean": 0.3,
        "stage_mean": 0.25,
        "grouped_mean": 0.2,
        "ridge-1": 0.11,
        "ridge-10": 0.105,
        "forest-6": 0.09,
        "forest-12": 0.095,
        "hist-15": 0.092,
        "hist-31": 0.1,
    }
    tuning = {case: {name: [{"mae": mae}] * 3 for name, mae in means.items()} for case in worlds}
    choices = training_choices(tuning, config["search"])
    cases = [d["case_id"] for d in config["datasets"]]
    outer = {
        **{name: means[name] for name in BASELINES},
        "ridge-10": 0.1009,
        "forest-6": 0.1,
        "hist-15": 0.1005,
    }
    evaluations = {
        case: {
            name: {
                "overall": {
                    "mae": mae,
                    "p95_positive_error": 0.4 if name in BASELINES else 0.2,
                    "worst_absolute_error": 0.6 if name in BASELINES else 0.3,
                },
                "slices": {"stage": {stage: {"mae": mae} for stage in ("sewing", "packing")}},
            }
            for name, mae in outer.items()
        }
        for case in cases
    }
    return config, tuning, choices, evaluations


def test_promotion_requires_all_gates_and_prefers_simplicity_within_tolerance(evidence):
    config, tuning, choices, evaluations = evidence
    first = select_model(tuning, evaluations, choices, config["selection"])
    assert first == select_model(tuning, evaluations, choices, config["selection"])
    assert first["selected_model"] == "ridge-10"
    assert first["status"] == "ML_PROMOTED_FOR_OFFLINE_SYNTHETIC_REVIEW"
    assert all(all(report["gates"].values()) for report in first["candidate_checks"].values())
    assert first["capacity_application_authorized"] is first["final_test_evaluated"] is False


@pytest.mark.parametrize(
    "kind",
    [
        "one_world",
        "temporal",
        "stage",
        "stress_seed",
        "overprediction",
        "worst_error",
        "small_gain",
    ],
)
def test_good_average_cannot_hide_a_failed_promotion_gate(evidence, kind):
    config, tuning, choices, evaluations = copy.deepcopy(evidence)
    for name in choices["family_finalists"].values():
        if kind == "one_world":
            evaluations["benchmark-42-baseline"][name]["overall"]["mae"] = 0.21
        elif kind == "temporal":
            tuning["benchmark-42-baseline"][name] = [{"mae": 0.21}, {"mae": 0.21}, {"mae": 0.01}]
        elif kind == "stage":
            evaluations["benchmark-42-baseline"][name]["slices"]["stage"]["sewing"]["mae"] = 0.3
        elif kind == "stress_seed":
            evaluations["development-19-disruption"][name]["overall"]["mae"] = 0.23
        elif kind == "overprediction":
            evaluations["benchmark-42-baseline"][name]["overall"]["p95_positive_error"] = 0.5
        elif kind == "worst_error":
            evaluations["benchmark-42-baseline"][name]["overall"]["worst_absolute_error"] = 0.7
        else:
            for reports in evaluations.values():
                reports[name]["overall"]["mae"] = 0.195
    decision = select_model(tuning, evaluations, choices, config["selection"])
    assert decision["status"] == "NO_ML_PROMOTION"
    assert decision["selected_model"] == choices["reference_baseline"]
    assert all(not c["eligible"] for c in decision["candidate_checks"].values())


def test_perfect_baseline_fallback_is_json_serializable(evidence):
    config, tuning, choices, evaluations = evidence
    for reports in evaluations.values():
        for name in BASELINES:
            reports[name]["overall"]["mae"] = 0
            reports[name]["overall"]["p95_positive_error"] = 0
            reports[name]["overall"]["worst_absolute_error"] = 0
            for summary in reports[name]["slices"]["stage"].values():
                summary["mae"] = 0
    decision = select_model(tuning, evaluations, choices, config["selection"])
    assert decision["status"] == "NO_ML_PROMOTION"
    json.dumps(decision, allow_nan=False)
