"""Research designation from training folds only; no validation input or promotion authority."""

from math import isfinite

from loometric.synthetic_training.selection import macro_profile


def change(value: float, reference: float) -> float:
    return 100 * (value - reference) / reference if reference else 0 if value == 0 else float("inf")


def reported(value: float) -> float | None:
    return value if isfinite(value) else None


def choose_candidate(
    evaluations: dict, temporal: dict, candidates: list[str], policy: dict
) -> dict:
    """Only newly declared original-training OOF evidence is accepted here."""
    scores = {
        name: macro_profile(
            {case: values[name]["overall"]["mae"] for case, values in evaluations.items()}
        )
        for name in ["grouped_mean", "forest-12", "hist-31", *candidates]
    }
    raw = min(("forest-12", "hist-31"), key=lambda name: (scores[name], name))
    checks = {}
    for name in candidates:
        stage = max(
            change(summary["mae"], models["grouped_mean"]["slices"]["stage"][key]["mae"])
            for models in evaluations.values()
            for key, summary in models[name]["slices"]["stage"].items()
        )
        tails = {
            key: max(
                change(models[name]["overall"][key], models["grouped_mean"]["overall"][key])
                for models in evaluations.values()
            )
            for key in ("p95_positive_error", "worst_absolute_error")
        }
        wins = {
            case: sum(
                a["mae"] < b["mae"] - 1e-12
                for a, b in zip(models[name], models["grouped_mean"], strict=True)
            )
            for case, models in temporal.items()
        }
        gates = {
            "macro_gain_vs_group": change(scores[name], scores["grouped_mean"])
            <= -policy["minimum_macro_gain_vs_group_percent"],
            "macro_gain_vs_best_raw": change(scores[name], scores[raw])
            <= -policy["minimum_macro_gain_vs_best_raw_percent"],
            "every_world_improves_vs_group": all(
                models[name]["overall"]["mae"] < models["grouped_mean"]["overall"]["mae"] - 1e-12
                for models in evaluations.values()
            ),
            "temporal_wins": min(wins.values()) >= policy["minimum_temporal_wins_per_world"],
            "stage_guard": stage <= policy["maximum_stage_regression_percent"] + 1e-12,
            "positive_p95_guard": tails["p95_positive_error"]
            <= policy["maximum_positive_p95_regression_percent"] + 1e-12,
            "worst_error_guard": tails["worst_absolute_error"]
            <= policy["maximum_worst_error_regression_percent"] + 1e-12,
        }
        checks[name] = {
            "eligible": all(gates.values()),
            "gates": gates,
            "macro_mae": scores[name],
            "macro_gain_vs_group_percent": reported(-change(scores[name], scores["grouped_mean"])),
            "macro_gain_vs_best_raw_percent": reported(-change(scores[name], scores[raw])),
            "maximum_stage_regression_percent": reported(stage),
            "tail_regression_percent": {k: reported(v) for k, v in tails.items()},
            "temporal_wins": wins,
        }
    eligible = [name for name in candidates if checks[name]["eligible"]]
    ranked = min(candidates, key=lambda name: (scores[name], policy["preference"].index(name)))
    selected = None
    if eligible:
        best = min(scores[name] for name in eligible)
        selected = min(
            (
                name
                for name in eligible
                if scores[name] <= best * (1 + policy["simplicity_tolerance_percent"] / 100)
            ),
            key=policy["preference"].index,
        )
    return {
        "status": "RESEARCH_CANDIDATE" if selected else "NO_RESEARCH_CANDIDATE",
        "selected_candidate": selected,
        "lowest_mae_candidate": ranked,
        "strongest_raw_reference": raw,
        "macro_mae": scores,
        "checks": checks,
        "selection_scope": "NEW_ORIGINAL_TRAINING_FOLDS_ONLY_ALREADY_USED_DEVELOPMENT_DATA",
        "validation_used_for_selection": False,
        "promotion_decision": "NO_ML_PROMOTION",
        "serving_change_authorized": False,
    }
