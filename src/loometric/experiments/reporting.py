"""Readable EXP-001 evidence, kept separate from experiment arithmetic."""

from __future__ import annotations

import platform
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TYPE_CHECKING

from loometric.data.validation import ValidationResult

if TYPE_CHECKING:
    from loometric.experiments.naive import ExperimentResult


def _installed_version(package: str) -> str:
    try:
        return version(package)
    except PackageNotFoundError:
        return "not installed (optional development tool)"


def render_report(
    result: ExperimentResult,
    validation: ValidationResult,
    *,
    runtime_seconds: float,
    dataset_path: Path,
    config_path: Path,
) -> str:
    """Report measured validation results; test metadata contains no performance estimates."""
    global_metrics = result.validation_metrics["global_mean"]
    department_metrics = result.validation_metrics["department_mean"]
    change = department_metrics.mae - global_metrics.mae
    relative = f"{100 * change / global_metrics.mae:+.4f}%" if global_metrics.mae else "undefined"
    worse_departments = (
        ", ".join(
            name
            for name, score in sorted(result.department_scores.items())
            if score.department_mae > score.global_mae
        )
        or "none"
    )
    winner = "global mean" if change > 0 else "department mean" if change < 0 else "a tie"
    config = result.split
    parts = [
        "# EXP-001: Naive productivity baselines",
        "Status: executed on training and validation data only. Final test remains reserved.",
        "## Objective and hypothesis",
        "Establish transparent reference errors for pre-shift productivity forecasting before "
        "Linear Regression or other ML algorithms. Hypothesis: department-specific historical "
        "training means may reduce validation MAE compared with a global training mean. "
        "MAE is the primary comparison metric; RMSE, R², bias, and slices provide context.",
        "## Data and prediction-time assumptions",
        f"Source: `{dataset_path.as_posix()}`  \nDataset SHA-256: `{config.dataset_sha256}`  \n"
        f"Frozen split configuration: `{config_path.as_posix()}`.",
        "The existing text loader, normalization, and validation checks run before splitting. "
        "They retain missing WIP, fractional staffing, and productivity above 1. The historical "
        "A01 profile describes the entire source CSV; it is not an untouched exploratory holdout. "
        "No test performance is computed here and no test targets estimate baseline parameters.",
        "Prediction cutoff: immediately before the scheduled shift. The department assignment "
        "must be known at that time. Global predictions use no features; department predictions "
        "use only normalized scheduled department. Date chooses the partition. All training "
        "outcomes must have been finalized before the validation period begins. The row key "
        "(date, department, team) remains a working assumption because shift IDs are absent.",
        "Excluded inputs: actual_productivity (label only), incentive, idle_time, idle_men, "
        "over_time, wip, targeted_productivity, smv, no_of_workers, no_of_style_change, quarter, "
        "day, and team. No aggregate includes validation or final test outcomes. "
        "No clipping, imputation, scaling, feature selection, or fitted encoding is performed.",
        "### Validation findings inherited from the source checks",
    ]
    parts.append(
        "\n".join(
            f"- {issue.severity}: {issue.message} Count: {issue.count}."
            for issue in validation.issues
        )
        or "No source validation warnings."
    )
    parts.extend(
        [
            "## Frozen evaluation protocol",
            f"Strategy: `{config.strategy}`. Sort a copy stably by date. For n distinct dates, "
            "use boundaries floor(3n/5) and floor(4n/5), selected without target values or model "
            "results. This approximates 60/20/20 by observed dates; row counts need not follow "
            "the same proportions. No dates are moved to balance departments or improve metrics.",
        ]
    )
    uses = {
        "train": "Estimate means",
        "validation": "Compare baselines",
        "test": "Reserved; no metrics",
    }
    split_rows = [
        "| Partition | First date (inclusive) | Last date (inclusive) | Dates | Rows | Use |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for name in ("train", "validation", "test"):
        bounds = getattr(config, name)
        split_rows.append(
            f"| {name} | {bounds.start} | {bounds.end} | {bounds.distinct_dates} "
            f"| {bounds.rows} | {uses[name]} |"
        )
    parts.append("\n".join(split_rows))
    n_dates = sum(getattr(config, name).distinct_dates for name in uses)
    parts.extend(
        [
            "",
            f"There are {n_dates} observed dates: {config.train.distinct_dates / n_dates:.2%} "
            f"training, {config.validation.distinct_dates / n_dates:.2%} validation, and "
            f"{config.test.distinct_dates / n_dates:.2%} final test. Boundaries require "
            "max(train date) < min(validation date) and max(validation date) < min(test date). "
            "Every row on a date stays together and every source row appears exactly once. "
            "The source fingerprint, counts, policy, and boundaries must match on reuse; "
            "a changed file fails rather than silently selecting new partitions.",
            "## Baseline definitions and training statistics",
            f"Global mean: mean of the {config.train.rows} training targets, "
            f"**{result.global_mean:.12f}**, predicted for every validation record.",
            "Department mean: mean of training targets within each normalized department. "
            "An unknown or missing department at prediction time falls back to the global "
            "training mean; it never uses validation statistics. The source loader still rejects "
            "unknown/missing departments in this historical dataset. No fallback is needed when "
            "every validation department has training observations.",
            "\n".join(
                [
                    "| Training department | Target mean |",
                    "| --- | --- |",
                    *[
                        f"| {name} | {mean:.12f} |"
                        for name, mean in sorted(result.department_means.items())
                    ],
                ]
            ),
            "",
            "Both estimators are row-weighted arithmetic means. They are fixed throughout "
            "validation, not expanding-window predictors. No stochastic operations, seed, "
            "hyperparameters, fitted ML algorithms, or model selection search are involved.",
            "## Measured validation performance",
            "All errors are in productivity-ratio units; R² is dimensionless. "
            "Bias is mean(prediction − actual), so positive bias means overprediction. "
            "R² = 1 − SSE/SST with the validation-target mean used only in its denominator; "
            "it is undefined for fewer than two observations or a constant target. "
            "All validation rows are included with equal weight.",
        ]
    )
    metric_rows = [
        "| Baseline | Training n | Validation n | MAE | RMSE | R² | Prediction bias |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, metrics in result.validation_metrics.items():
        r2 = f"{metrics.r2:.9f}" if metrics.r2 is not None else "undefined"
        metric_rows.append(
            f"| {name} | {config.train.rows} | {metrics.samples} | {metrics.mae:.9f} "
            f"| {metrics.rmse:.9f} | {r2} | {metrics.bias:+.9f} |"
        )
    parts.append("\n".join(metric_rows))
    parts.extend(
        [
            "",
            "### Department-level validation MAE",
            "\n".join(
                [
                    "| Department | Training n | Validation n | Global MAE | Department MAE |",
                    "| --- | --- | --- | --- | --- |",
                    *[
                        f"| {name} | {score.training_samples} | {score.validation_samples} "
                        f"| {score.global_mae:.9f} | {score.department_mae:.9f} |"
                        for name, score in sorted(result.department_scores.items())
                    ],
                ]
            ),
            "",
            "### Comparison",
            f"Department mean minus global mean validation MAE: **{change:+.9f}** "
            f"(**{relative}** relative to the global mean baseline). A negative change is an "
            f"improvement. The primary-metric comparison favors **{winner}**. This is a "
            "validation comparison between two predefined references, not final model evaluation "
            "or evidence of production readiness.",
            f"Departments where the department predictor has higher MAE: {worse_departments}. "
            "An aggregate improvement does not imply improvement in every department. "
            "Negative R² means squared error exceeds the constant validation-mean reference "
            "used in the R² denominator; that reference is not a deployable fitted predictor.",
            "## Limitations and leakage risks",
            "The history is short and from one source context; departments and teams recur. "
            "This measures later dates for familiar operations, not generalization to unseen "
            "factories or teams. Averaging within departments does not establish a causal effect. "
            "Validation errors can reflect temporal changes that fixed means cannot track.",
            "Measurement timestamps, shift timing, row grain, productivity units, and values "
            "above 1 still need domain confirmation. A01 already profiled all source dates and "
            "targets; keep that known limitation distinct from the performance holdout. Repeated "
            "validation comparisons in future experiments can overfit the development period. "
            "The final test partition must stay fixed and must not be evaluated until one model "
            "and its preprocessing are frozen using training/validation only.",
            "## Reproduction and environment",
            "From the repository root with the local CSV and committed split configuration:",
            "\n".join(
                [
                    "```powershell",
                    ".\\.venv\\Scripts\\python.exe -m pip install -r requirements/exp-001.txt",
                    ".\\.venv\\Scripts\\python.exe -m pip install "
                    "--no-build-isolation --no-deps -e .",
                    ".\\.venv\\Scripts\\python.exe -m loometric.experiments.naive "
                    f"--dataset '{dataset_path.as_posix().replace(chr(39), chr(39) * 2)}' "
                    f"--split-config '{config_path.as_posix().replace(chr(39), chr(39) * 2)}'",
                    "```",
                ]
            ),
            "The split configuration is created once with `python -m loometric.data.splitting`; "
            "that command refuses to overwrite an existing configuration. Normal experiment "
            "runs only read it. Do not regenerate partitions during later model comparisons.",
            f"Python: **{platform.python_version()}**. "
            + "; ".join(
                f"{package}: **{_installed_version(package)}**"
                for package in ("pandas", "numpy", "pytest", "ruff")
            )
            + ".",
            "Measured load/validate/split/predict/score wall time: "
            f"**{runtime_seconds:.6f} seconds** "
            "(report rendering/writing excluded). Runtime varies between runs; fitted means, "
            "partitions, predictions, and metrics are deterministic for identical inputs "
            "and environment.",
            "Exact environment pins are recorded in `requirements/exp-001.txt`; this is the "
            "initial Python 3.13 environment snapshot, not a cross-platform wheel/hash lock.",
            "## Recommended next experiment",
            "EXP-002: an interpretable Linear Regression using the same frozen partitions and "
            "only confirmed pre-shift features. Fit any categorical encoding on training rows "
            "only, compare validation MAE/RMSE and slices against both EXP-001 references, "
            "and leave final test performance uncalculated. No such model is implemented here.",
        ]
    )
    return "\n\n".join(part for part in parts if part) + "\n"
