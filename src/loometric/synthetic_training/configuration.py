"""Bounded predeclared experiment configuration and fixed scientific policy identity."""

from pathlib import Path

from loometric.prediction.contracts import read_json
from loometric.synthetic_training.data import require

POLICY_VERSION = "synthetic-training-v1"
BASELINES = ("global_mean", "stage_mean", "grouped_mean")


def load_study(path: Path) -> dict:
    require(path.stat().st_size <= 65536, "STUDY_CONFIGURATION_BYTE_LIMIT")
    config = read_json(path.read_text(encoding="utf-8"))
    require(
        set(config)
        == {
            "schema_version",
            "experiment_id",
            "policy_version",
            "model_seed",
            "folds",
            "search",
            "selection",
            "risk",
            "artifact_case",
            "datasets",
        },
        "CLOSED_STUDY_SCHEMA_REQUIRED",
    )
    require(
        type(config["schema_version"]) is int
        and config["schema_version"] == 1
        and config["experiment_id"] == "EXP-006"
        and config["policy_version"] == POLICY_VERSION
        and type(config["model_seed"]) is int
        and 0 <= config["model_seed"] < 2**32,
        "UNSUPPORTED_STUDY_POLICY",
    )
    require(
        config["folds"]
        == {
            "evaluation_start_fractions": [[1, 2], [2, 3], [5, 6]],
            "evaluation_width_fraction": [1, 6],
            "purged_dates": 1,
        },
        "FROZEN_TEMPORAL_POLICY_REQUIRED",
    )
    require(
        isinstance(config["search"], list) and len(config["search"]) == 6, "BOUNDED_SEARCH_REQUIRED"
    )
    families, names = [], set()
    for spec in config["search"]:
        require(
            set(spec) == {"name", "family", "parameters"}
            and isinstance(spec["name"], str)
            and spec["name"] not in names,
            "CLOSED_UNIQUE_MODEL_CONFIGURATION_REQUIRED",
        )
        names.add(spec["name"])
        family, params = spec["family"], spec["parameters"]
        families.append(family)
        bounds = {
            "ridge": {"alpha": (1, 10000)},
            "forest": {
                "n_estimators": (1, 200),
                "max_depth": (1, 12),
                "min_samples_leaf": (5, 100),
            },
            "hist": {
                "max_iter": (1, 200),
                "max_leaf_nodes": (2, 31),
                "l2_regularization": (0, 100),
            },
        }
        require(
            family in bounds and set(params) == set(bounds[family]),
            "UNSUPPORTED_ESTIMATOR_PARAMETERS",
        )
        for key, (low, high) in bounds[family].items():
            require(
                type(params[key]) is int and low <= params[key] <= high, "ESTIMATOR_RESOURCE_BOUND"
            )
    require(
        sorted(families) == ["forest", "forest", "hist", "hist", "ridge", "ridge"],
        "DECLARED_MODEL_FAMILIES_REQUIRED",
    )
    selection = config["selection"]
    require(
        set(selection)
        == {
            "minimum_macro_improvement_percent",
            "minimum_temporal_wins_per_world",
            "maximum_stage_regression_percent",
            "maximum_stress_seed_regression_percent",
            "maximum_overprediction_p95_regression_percent",
            "maximum_worst_error_regression_percent",
            "simplicity_tolerance_percent",
            "family_preference",
        },
        "CLOSED_SELECTION_POLICY_REQUIRED",
    )
    require(
        selection["family_preference"] == ["ridge", "hist", "forest"]
        and all(
            type(value) is int and 0 <= value <= 100
            for key, value in selection.items()
            if key != "family_preference"
        )
        and 1 <= selection["minimum_temporal_wins_per_world"] <= 3,
        "BOUNDED_PROMOTION_GATES_REQUIRED",
    )
    require(
        config["risk"]
        == {
            "absolute_residual_quantile": 0.9,
            "minimum_stage_oof_rows": 30,
            "interpretation": "DEVELOPMENT_RESIDUAL_BAND_NOT_CALIBRATED",
        },
        "FROZEN_RISK_POLICY_REQUIRED",
    )
    expected_cases = {
        f"development-{seed}-{scenario}"
        for seed in (19, 42, 73)
        for scenario in ("baseline", "disruption", "workload_surge")
    } | {"benchmark-42-baseline"}
    require(
        isinstance(config["datasets"], list)
        and len(config["datasets"]) == 10
        and {d["case_id"] for d in config["datasets"]} == expected_cases
        and config["artifact_case"] == "benchmark-42-baseline",
        "DECLARED_DATASET_FAMILY_REQUIRED",
    )
    for binding in config["datasets"]:
        require(
            set(binding)
            == {
                "case_id",
                "directory",
                "expected_manifest_fingerprint",
                "profile",
                "seed",
                "scenario",
            }
            and binding["case_id"]
            == f"{binding['profile']}-{binding['seed']}-{binding['scenario']}"
            and isinstance(binding["directory"], str)
            and not Path(binding["directory"]).is_absolute()
            and ".." not in Path(binding["directory"]).parts,
            "CLOSED_DATASET_BINDING_REQUIRED",
        )
    return config
