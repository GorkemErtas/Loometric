"""Training-only joint support and selection-reused conditional residual diagnostics."""

import numpy as np
import pandas as pd

from loometric.synthetic_training.metrics import error_summary

CELL_COLUMNS = ("stage", "shift_kind", "staffing_band", "workload_band")


def fit_support(metadata: pd.DataFrame) -> dict:
    return {
        "joint_cells": {
            tuple(key): len(group) for key, group in metadata.groupby(list(CELL_COLUMNS), sort=True)
        },
        "load_minimum": float(metadata.planned_load_ratio.min()),
        "load_maximum": float(metadata.planned_load_ratio.max()),
    }


def risk_flags(metadata: pd.DataFrame, reference: dict, policy: dict) -> pd.DataFrame:
    count = [
        reference["joint_cells"].get(tuple(row), 0)
        for row in metadata.loc[:, CELL_COLUMNS].itertuples(index=False, name=None)
    ]
    return pd.DataFrame(
        {
            "sparse_joint_context": np.asarray(count) < policy["minimum_joint_support"],
            "outside_training_load": (metadata.planned_load_ratio < reference["load_minimum"])
            | (metadata.planned_load_ratio > reference["load_maximum"]),
            "high_planned_load": metadata.planned_load_ratio > policy["high_load_threshold"],
        },
        index=metadata.index,
    )


def residual_profile(actual, predicted, metadata, policy: dict) -> dict:
    errors = (predicted - actual).abs()
    radius = float(np.quantile(errors, policy["residual_quantile"]))
    stages, cells = {}, {}
    for stage, index in metadata.groupby("stage", sort=True).groups.items():
        stages[str(stage)] = (
            float(np.quantile(errors.loc[index], policy["residual_quantile"]))
            if len(index) >= policy["minimum_residual_support"]
            else radius
        )
    for (stage, band), index in metadata.groupby(
        ["stage", "workload_band"], sort=True
    ).groups.items():
        cells[f"{stage}|{band}"] = {
            "samples": len(index),
            "radius": float(np.quantile(errors.loc[index], policy["residual_quantile"]))
            if len(index) >= policy["minimum_residual_support"]
            else stages[str(stage)],
            "fallback_to_stage": len(index) < policy["minimum_residual_support"],
        }
    return {
        "global_radius": radius,
        "stage_radii": stages,
        "stage_load_radii": cells,
        "coverage_guarantee": False,
        "selection_reused_folds": True,
        "interpretation": "DESCRIPTIVE_CONDITIONAL_OOF_RESIDUALS_NOT_CALIBRATED",
    }


def risk_diagnostics(population, predicted, support: dict, residuals: dict, policy: dict) -> dict:
    metadata, actual = population.metadata, population.y
    flags = risk_flags(metadata, support, policy)
    summaries = {}
    for flag in flags:
        summaries[flag] = {}
        for value in (False, True):
            ids = flags.index[flags[flag].eq(value)]
            summaries[flag][str(value)] = {
                "samples": len(ids),
                "metrics": error_summary(actual.loc[ids], predicted.loc[ids]) if len(ids) else None,
            }
    radii = np.array(
        [
            residuals["stage_load_radii"].get(
                f"{row.stage}|{row.workload_band}",
                {"radius": residuals["stage_radii"].get(row.stage, residuals["global_radius"])},
            )["radius"]
            for row in metadata.itertuples()
        ]
    )
    stage = np.array(
        [residuals["stage_radii"].get(s, residuals["global_radius"]) for s in metadata.stage]
    )
    errors = (predicted - actual).abs().to_numpy()
    return {
        "feature_only_risk_slices": summaries,
        "conditional_oof_band": {
            "empirical_coverage": float(np.mean(errors <= radii)),
            "mean_width": float(2 * np.mean(radii)),
        },
        "stage_oof_band": {
            "empirical_coverage": float(np.mean(errors <= stage)),
            "mean_width": float(2 * np.mean(stage)),
        },
        "coverage_guarantee": False,
        "selection_reused_folds": True,
        "hidden_shift_detection_claim": False,
    }
