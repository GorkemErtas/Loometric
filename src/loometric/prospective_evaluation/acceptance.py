"""Frozen EXP-009 replication guards; promotion is unconditionally prohibited."""

from loometric.prospective_evaluation.diagnostics import METRICS, macro


def relative_check(candidate, reference, percent, *, gain=False):
    if candidate is None or reference is None:
        return {"passed": False, "percent": None}
    if reference == 0:
        return {"passed": candidate == 0 and not gain, "percent": None}
    change = (
        100 * (reference - candidate) / reference
        if gain
        else 100 * (candidate - reference) / reference
    )
    limit = reference * (1 - percent / 100 if gain else 1 + percent / 100)
    return {"passed": candidate <= limit, "percent": change}


def evaluate_acceptance(diagnostics, designs, compared, config):
    minimum = config["sample_size"]
    thresholds = config["acceptance"]
    counts, checks = {}, {}
    indexed = {(d.case.world_id, d.case.condition): diagnostics[d.case.case_id] for d in designs}
    worlds = sorted({d.case.world_id for d in designs})
    models = [m["name"] for m in config["models"]]
    macro_metrics = {
        condition: {
            m: macro([indexed[w, condition]["models"][m]["metrics"] for w in worlds])
            for m in models
        }
        for condition in ("baseline", "disruption")
    }
    for design in designs:
        case = design.case.case_id
        groups = diagnostics[case]["models"]["grouped_mean"]
        valid = groups["defined_target_counts"]
        counts[case] = (
            valid["rows"] >= minimum["minimum_valid_targets_per_case"]
            and valid["dates"] >= minimum["minimum_score_dates_with_valid_targets"]
        )
        for stage, cell in groups["subgroups"]["stage"].items():
            n = cell["defined_target_counts"]
            counts[f"{case}|{stage}"] = (
                n["rows"] >= minimum["minimum_valid_targets_per_stage_case"]
                and n["dates"] >= minimum["minimum_stage_dates_with_valid_targets"]
                and n["lines"] >= minimum["minimum_stage_lines"]
                and n["crews"] >= minimum["minimum_stage_crews"]
            )
            candidate = diagnostics[case]["models"]["rf_physics"]["subgroups"]["stage"][stage][
                "metrics"
            ]["mae"]
            checks[f"stage|{case}|{stage}"] = relative_check(
                candidate,
                cell["metrics"]["mae"],
                thresholds["maximum_stage_mae_regression_vs_group_percent"],
            )
        for metric, threshold in (
            ("p95_absolute_error", "maximum_p95_absolute_regression_vs_group_percent"),
            ("p95_positive_error", "maximum_p95_positive_regression_vs_group_percent"),
            ("worst_absolute_error", "maximum_worst_error_regression_vs_group_percent"),
        ):
            checks[f"{metric}|{case}"] = relative_check(
                diagnostics[case]["models"]["rf_physics"]["metrics"][metric],
                groups["metrics"][metric],
                thresholds[threshold],
            )
        if design.case.condition == "baseline":
            checks[f"world_forest|{case}"] = relative_check(
                diagnostics[case]["models"]["rf_physics"]["metrics"]["mae"],
                diagnostics[case]["models"]["random_forest"]["metrics"]["mae"],
                thresholds["maximum_baseline_world_regression_vs_forest_percent"],
            )
        else:
            checks[f"disruption_seed|{case}"] = relative_check(
                diagnostics[case]["models"]["rf_physics"]["metrics"]["mae"],
                groups["metrics"]["mae"],
                thresholds["maximum_disruption_seed_mae_regression_vs_group_percent"],
            )
    baseline, disruption = macro_metrics["baseline"], macro_metrics["disruption"]
    checks["baseline_macro_gain_group"] = relative_check(
        baseline["rf_physics"]["mae"],
        baseline["grouped_mean"]["mae"],
        thresholds["minimum_baseline_macro_mae_gain_vs_group_percent"],
        gain=True,
    )
    checks["baseline_macro_gain_forest"] = relative_check(
        baseline["rf_physics"]["mae"],
        baseline["random_forest"]["mae"],
        thresholds["minimum_baseline_macro_mae_gain_vs_forest_percent"],
        gain=True,
    )
    wins = sum(v is not None and v < 0 for v in compared["primary"]["individual_worlds"].values())
    checks["baseline_world_wins"] = {
        "passed": wins >= thresholds["minimum_baseline_world_wins_vs_forest"],
        "wins": wins,
    }
    upper = compared["primary"]["interval"][1]
    checks["primary_world_interval"] = {
        "passed": upper is not None
        and upper < thresholds["primary_world_interval_upper_bound_must_be_below"],
        "upper": upper,
    }
    checks["disruption_macro"] = relative_check(
        disruption["rf_physics"]["mae"],
        disruption["grouped_mean"]["mae"],
        thresholds["maximum_disruption_macro_mae_regression_vs_group_percent"],
    )
    status = (
        "INCONCLUSIVE"
        if not all(counts.values())
        else "REPLICATION_NOT_SUPPORTED"
        if not all(c["passed"] for c in checks.values())
        else "FROZEN_CANDIDATE_REPLICATION_SUPPORTED"
    )
    return {
        "provisional_status": status,
        "requires_verified_reproduction": True,
        "minimum_counts": counts,
        "numerical_guards": checks,
        "macro_metrics": macro_metrics,
        "metric_names": list(METRICS),
        "promotion_decision": "NO_ML_PROMOTION",
        "capacity_application_authorized": False,
    }
