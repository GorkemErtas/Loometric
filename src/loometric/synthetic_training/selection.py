"""Predeclared multi-population gates; no forced promotion or reserved-test input."""

from math import fsum, isfinite

from loometric.synthetic_training.configuration import BASELINES
from loometric.synthetic_training.data import require


def macro_profile(values: dict[str, float]) -> float:
    development = [v for name, v in values.items() if name.startswith("development-")]
    benchmark = [v for name, v in values.items() if name.startswith("benchmark-")]
    require(
        len(development) == 3 and len(benchmark) == 1 and len(values) == 4,
        "FOUR_BASELINE_WORLDS_REQUIRED",
    )
    return 0.5 * fsum(development) / 3 + 0.5 * benchmark[0]


def training_choices(tuning: dict, specs: list[dict]) -> dict:
    names = [*BASELINES, *(s["name"] for s in specs)]
    scores = {
        name: macro_profile(
            {
                case: fsum(f["mae"] for f in models[name]) / len(models[name])
                for case, models in tuning.items()
            }
        )
        for name in names
    }
    reference = min(BASELINES, key=lambda name: (round(scores[name], 12), BASELINES.index(name)))
    families = {
        family: min(
            (s["name"] for s in specs if s["family"] == family),
            key=lambda name: (round(scores[name], 12), names.index(name)),
        )
        for family in ("ridge", "forest", "hist")
    }
    return {
        "reference_baseline": reference,
        "family_finalists": families,
        "training_fold_macro_mae": scores,
    }


def _ratio_change(value: float, reference: float) -> float:
    return 100 * (value - reference) / reference if reference else 0 if value == 0 else float("inf")


def _reported_percent(value: float) -> float | None:
    return value if isfinite(value) else None


def select_model(tuning: dict, evaluations: dict, choices: dict, policy: dict) -> dict:
    reference = choices["reference_baseline"]
    baseline_cases = [case for case in evaluations if case.endswith("-baseline")]

    def outer_score(name):
        return macro_profile(
            {case: evaluations[case][name]["overall"]["mae"] for case in baseline_cases}
        )

    best_outer_naive = min(
        BASELINES, key=lambda name: (round(outer_score(name), 12), BASELINES.index(name))
    )
    checks = {}
    for family, name in choices["family_finalists"].items():
        macro_gain = -_ratio_change(outer_score(name), outer_score(reference))
        strongest_gain = -_ratio_change(outer_score(name), outer_score(best_outer_naive))
        per_world = {
            case: -_ratio_change(
                evaluations[case][name]["overall"]["mae"],
                evaluations[case][reference]["overall"]["mae"],
            )
            for case in baseline_cases
        }
        temporal = {
            case: sum(
                a["mae"] < b["mae"] - 1e-12
                for a, b in zip(models[name], models[reference], strict=True)
            )
            for case, models in tuning.items()
        }
        stage_changes = {
            f"{case}|{stage}": _ratio_change(
                summary["mae"], reports[reference]["slices"]["stage"][stage]["mae"]
            )
            for case, reports in evaluations.items()
            for stage, summary in reports[name]["slices"]["stage"].items()
        }
        stress = {}
        for scenario in ("disruption", "workload_surge"):
            cases = [case for case in evaluations if case.endswith("-" + scenario)]
            require(len(cases) == 3, "THREE_PAIRED_STRESS_WORLDS_REQUIRED")
            stress[scenario] = _ratio_change(
                fsum(evaluations[c][name]["overall"]["mae"] for c in cases) / 3,
                fsum(evaluations[c][reference]["overall"]["mae"] for c in cases) / 3,
            )
        worst_stress = max(
            _ratio_change(reports[name]["overall"]["mae"], reports[reference]["overall"]["mae"])
            for case, reports in evaluations.items()
            if not case.endswith("-baseline")
        )
        tails = {
            metric: max(
                _ratio_change(
                    reports[name]["overall"][metric], reports[reference]["overall"][metric]
                )
                for reports in evaluations.values()
            )
            for metric in ("p95_positive_error", "worst_absolute_error")
        }
        gates = {
            "macro_improvement": macro_gain >= policy["minimum_macro_improvement_percent"],
            "strongest_outer_naive_improvement": strongest_gain
            >= policy["minimum_macro_improvement_percent"],
            "every_baseline_world_improves": all(v > 1e-12 for v in per_world.values()),
            "temporal_wins": all(
                v >= policy["minimum_temporal_wins_per_world"] for v in temporal.values()
            ),
            "stage_guard": max(stage_changes.values())
            <= policy["maximum_stage_regression_percent"] + 1e-12,
            "stress_macro_guard": all(v <= 1e-12 for v in stress.values()),
            "stress_seed_guard": worst_stress
            <= policy["maximum_stress_seed_regression_percent"] + 1e-12,
            "overprediction_guard": tails["p95_positive_error"]
            <= policy["maximum_overprediction_p95_regression_percent"] + 1e-12,
            "worst_error_guard": tails["worst_absolute_error"]
            <= policy["maximum_worst_error_regression_percent"] + 1e-12,
        }
        checks[name] = {
            "family": family,
            "eligible": all(gates.values()),
            "gates": gates,
            "macro_mae": outer_score(name),
            "macro_improvement_percent": _reported_percent(macro_gain),
            "strongest_outer_naive_improvement_percent": _reported_percent(strongest_gain),
            "baseline_world_improvement_percent": {
                key: _reported_percent(value) for key, value in per_world.items()
            },
            "temporal_wins": temporal,
            "maximum_stage_regression_percent": _reported_percent(max(stage_changes.values())),
            "stress_macro_regression_percent": {
                key: _reported_percent(value) for key, value in stress.items()
            },
            "maximum_stress_seed_regression_percent": _reported_percent(worst_stress),
            "tail_regression_percent": {
                key: value if value != float("inf") else None for key, value in tails.items()
            },
        }
    eligible = [name for name, report in checks.items() if report["eligible"]]
    selected = reference
    if eligible:
        best = min(checks[name]["macro_mae"] for name in eligible)
        close = [
            name
            for name in eligible
            if checks[name]["macro_mae"]
            <= best * (1 + policy["simplicity_tolerance_percent"] / 100) + 1e-12
        ]
        selected = min(
            close,
            key=lambda name: (policy["family_preference"].index(checks[name]["family"]), name),
        )
    return {
        "status": "ML_PROMOTED_FOR_OFFLINE_SYNTHETIC_REVIEW" if eligible else "NO_ML_PROMOTION",
        "selected_model": selected,
        "reference_baseline": reference,
        "strongest_outer_naive": best_outer_naive,
        "candidate_checks": checks,
        "final_test_evaluated": False,
        "capacity_application_authorized": False,
    }
