"""Bounded offline tuning and paired validation; no test population or serving path."""

from collections import Counter
from dataclasses import dataclass
from time import perf_counter

import pandas as pd
from threadpoolctl import threadpool_limits

from loometric.execution import peak_working_set_bytes
from loometric.synthetic_ml.storage import digest
from loometric.synthetic_training.configuration import BASELINES
from loometric.synthetic_training.data import DevelopmentData, Population, load_development, require
from loometric.synthetic_training.folds import expanding_folds
from loometric.synthetic_training.metrics import analyze, error_summary
from loometric.synthetic_training.models import build_model, model_metadata
from loometric.synthetic_training.risk import (
    assess_support,
    band_diagnostics,
    residual_reference,
    support_profile,
)
from loometric.synthetic_training.selection import select_model, training_choices


def load_datasets(config: dict, root) -> dict[str, DevelopmentData]:
    result = {}
    for binding in config["datasets"]:
        data = load_development(
            root / binding["directory"],
            expected_fingerprint=binding["expected_manifest_fingerprint"],
        )
        require(
            all(data.provenance[key] == binding[key] for key in ("profile", "seed", "scenario")),
            "SOURCE_WORLD_BINDING_MISMATCH",
        )
        require(
            len(data.train.X) <= 20000 and len(data.validation.X) <= 20000,
            "TRAINING_POPULATION_RESOURCE_BOUND",
        )
        result[binding["case_id"]] = data
    for case, data in result.items():
        base = case.removesuffix("-disruption").removesuffix("-workload_surge") + "-baseline"
        if data.provenance["scenario"] != "baseline":
            require(
                data.train.source_fingerprint == result[base].train.source_fingerprint,
                "STRESS_TRAINING_MUST_MATCH_BASELINE",
            )
    return result


class FitLedger:
    """Complexity/row/thread caps are hard declarations; wall checks occur between fits."""

    def __init__(self):
        self.started = perf_counter()
        self.fits = []
        self.measurements = []

    def fit(self, spec: dict, seed: int, population: Population, ids: list, case: str, scope: str):
        require(
            len(self.fits) < 144 and 0 < len(ids) <= 20000 and set(ids) <= set(population.X.index),
            "FIT_COUNT_OR_TRAINING_POPULATION_BOUND",
        )
        require(perf_counter() - self.started <= 600, "BETWEEN_FIT_WALL_BUDGET_EXCEEDED")
        X, y = population.X.loc[ids], population.y.loc[ids]
        before = digest({"X": X.to_dict(orient="split"), "y": list(y)})
        model = build_model(spec, seed)
        start = perf_counter()
        model.fit(X, y)
        seconds = perf_counter() - start
        require(
            before == digest({"X": X.to_dict(orient="split"), "y": list(y)}),
            "MODEL_MUTATED_TRAINING_INPUT",
        )
        self.fits.append(
            {
                "case": case,
                "scope": scope,
                "model": spec["name"],
                "samples": len(ids),
                "training_ids_fingerprint": digest(ids),
                "training_payload_fingerprint": before,
                "first_date": min(population.metadata.loc[ids, "start_date"]).isoformat(),
                "last_date": max(population.metadata.loc[ids, "start_date"]).isoformat(),
                "preprocessing": model_metadata(model),
            }
        )
        self.measurements.append(
            {
                "operation": "fit",
                "case": case,
                "scope": scope,
                "model": spec["name"],
                "seconds": seconds,
                "samples": len(ids),
                "process_lifetime_peak_working_set_bytes": peak_working_set_bytes(),
            }
        )
        return model

    def predict(self, model, X: pd.DataFrame, case: str, scope: str, name: str) -> pd.Series:
        start = perf_counter()
        values = model.predict(X)
        seconds = perf_counter() - start
        self.measurements.append(
            {
                "operation": "predict",
                "case": case,
                "scope": scope,
                "model": name,
                "seconds": seconds,
                "samples": len(X),
                "seconds_per_observation": seconds / len(X),
            }
        )
        return pd.Series(values, index=X.index, dtype="float64")


@dataclass
class StudyResult:
    report: dict
    selected_model: object
    selected_metadata: dict
    oof_predictions: list[dict]
    validation_predictions: list[dict]
    excluded_observations: list[dict]
    measurements: dict


def run_study(config: dict, datasets: dict[str, DevelopmentData], *, progress=None) -> StudyResult:
    require(
        set(datasets) == {d["case_id"] for d in config["datasets"]},
        "COMPLETE_STUDY_DATASETS_REQUIRED",
    )
    baseline_cases = sorted(case for case in datasets if case.endswith("-baseline"))
    all_specs = [
        {"name": name, "family": "naive", "parameters": {}} for name in BASELINES
    ] + config["search"]
    specs = {spec["name"]: spec for spec in all_specs}
    ledger = FitLedger()
    tuning, fold_descriptions, oof, outer_predictions = {}, {}, [], []
    with threadpool_limits(limits=1):
        for case in baseline_cases:
            data = datasets[case]
            tuning[case] = {name: [] for name in specs}
            folds = expanding_folds(data.train)
            fold_descriptions[case] = []
            for fold in folds:
                fold_descriptions[case].append(
                    {
                        "name": fold.name,
                        "train_dates": list(fold.train_dates),
                        "evaluation_dates": list(fold.evaluation_dates),
                        "train_rows": len(fold.train_ids),
                        "evaluation_rows": len(fold.evaluation_ids),
                        "purged_dates": 1,
                        "training_ids_fingerprint": digest(fold.train_ids),
                        "evaluation_ids_fingerprint": digest(fold.evaluation_ids),
                    }
                )
                for name, spec in specs.items():
                    model = ledger.fit(
                        spec,
                        config["model_seed"],
                        data.train,
                        list(fold.train_ids),
                        case,
                        fold.name,
                    )
                    index = list(fold.evaluation_ids)
                    predicted = ledger.predict(
                        model, data.train.X.loc[index], case, fold.name, name
                    )
                    tuning[case][name].append(error_summary(data.train.y.loc[index], predicted))
                    oof.extend(
                        {
                            "case": case,
                            "fold": fold.name,
                            "model": name,
                            "observation_id": oid,
                            "stage": data.train.metadata.loc[oid, "stage"],
                            "actual": float(data.train.y[oid]),
                            "prediction": float(predicted[oid]),
                        }
                        for oid in index
                    )
            if progress:
                progress(
                    {"stage": "training_folds_complete", "case": case, "fits": len(ledger.fits)}
                )
        choices = training_choices(tuning, config["search"])
        finalists = [*BASELINES, *choices["family_finalists"].values()]
        evaluations, profiles, references, models = {}, {}, {}, {}
        for case in baseline_cases:
            data = datasets[case]
            profiles[case] = support_profile(data.train.X, data.train.y)
            models[case], references[case] = {}, {}
            for name in finalists:
                models[case][name] = ledger.fit(
                    specs[name],
                    config["model_seed"],
                    data.train,
                    list(data.train.X.index),
                    case,
                    "full_original_training",
                )
                references[case][name] = residual_reference(
                    [r for r in oof if r["case"] == case and r["model"] == name]
                )
        for case, data in datasets.items():
            base = (
                case
                if case.endswith("-baseline")
                else case.removesuffix("-disruption").removesuffix("-workload_surge") + "-baseline"
            )
            if case != base:
                require(
                    data.train.source_fingerprint == datasets[base].train.source_fingerprint,
                    "PAIRED_STRESS_TRAINING_DRIFT",
                )
            evaluations[case] = {}
            inputs = data.validation.X.to_dict(orient="records")
            for name in finalists:
                predicted = ledger.predict(
                    models[base][name], data.validation.X, case, "outer_validation", name
                )
                report = analyze(data.validation.y, predicted, data.validation.metadata)
                statuses = [
                    assess_support(row, profiles[base], float(point))
                    for row, point in zip(inputs, predicted, strict=True)
                ]
                report["support_status_counts"] = dict(
                    sorted(Counter(s["status"] for s in statuses).items())
                )
                report["support_reason_counts"] = dict(
                    sorted(Counter(code for s in statuses for code in s["reason_codes"]).items())
                )
                report["risk_band"] = band_diagnostics(
                    data.validation.y, predicted, data.validation.metadata, references[base][name]
                )
                evaluations[case][name] = report
                outer_predictions.extend(
                    {
                        "case": case,
                        "model": name,
                        "observation_id": oid,
                        "actual": float(data.validation.y[oid]),
                        "prediction": float(predicted[oid]),
                        "stage": data.validation.metadata.loc[oid, "stage"],
                        "shift_kind": data.validation.metadata.loc[oid, "shift_kind"],
                        "demand_censored": bool(
                            data.validation.metadata.loc[oid, "demand_censored"]
                        ),
                        "support_status": status["status"],
                    }
                    for oid, status in zip(predicted.index, statuses, strict=True)
                )
            if progress:
                progress(
                    {
                        "stage": "validation_complete",
                        "case": case,
                        "observations": len(data.validation.X),
                    }
                )
    decision = select_model(tuning, evaluations, choices, config["selection"])
    canonical = config["artifact_case"]
    name = decision["selected_model"]
    report = {
        "schema_version": 1,
        "experiment_id": config["experiment_id"],
        "policy_version": config["policy_version"],
        "synthetic": True,
        "dataset_version": "synthetic-ml-v1",
        "target": "standard_capacity_attainment",
        "configuration_fingerprint": digest(config),
        "configuration": config,
        "datasets": {
            case: {"provenance": data.provenance, "audit": data.audit}
            for case, data in datasets.items()
        },
        "folds": fold_descriptions,
        "training_fold_metrics": tuning,
        "training_choices": choices,
        "validation": evaluations,
        "selection": decision,
        "support_profiles": profiles,
        "residual_references": references,
        "fit_provenance": ledger.fits,
        "model_fits": len(ledger.fits),
        "reserved_label_values_decoded": False,
        "final_test_evaluated": False,
        "capacity_application_authorized": False,
        "unseen_entity_evaluation": "DEFERRED_TO_SEPARATELY_APPROVED_RESERVED_EVALUATION",
        "undefined_label_policy": "AUDITED_EXCLUSIONS_NO_PREDICTION_OR_IMPUTATION",
        "world_independence_claim": False,
        "stress_models_refitted": False,
        "aggregation": "HALF_MEAN_OF_THREE_DEVELOPMENT_SEEDS_HALF_BENCHMARK; "
        "PAIRED_SCENARIOS_SEPARATE",
        "m08c_readiness": "OFFLINE_ARTIFACT_ONLY_NO_SERVING_OR_PLANNING_AUTHORIZATION",
    }
    selected_metadata = {
        "name": name,
        "specification": specs[name],
        "training_case": canonical,
        "training_partition": "train",
        "training_rows": len(datasets[canonical].train.X),
        "source": datasets[canonical].provenance,
        "support": profiles[canonical],
        "residual_reference": references[canonical][name],
        "preprocessing": model_metadata(models[canonical][name]),
        "validation": evaluations[canonical][name],
        "first_training_date": min(datasets[canonical].train.metadata.start_date).isoformat(),
        "last_training_date": max(datasets[canonical].train.metadata.start_date).isoformat(),
    }
    return StudyResult(
        report,
        models[canonical][name],
        selected_metadata,
        oof,
        outer_predictions,
        [
            {"case": case, "partition": partition, **record}
            for case, data in datasets.items()
            for partition in ("train", "validation")
            for record in getattr(data, partition).excluded
        ],
        {
            "elapsed_seconds": perf_counter() - ledger.started,
            "operations": ledger.measurements,
            "process_lifetime_peak_working_set_bytes": peak_working_set_bytes(),
            "memory_scope": "WHOLE_PROCESS_LIFETIME_NOT_PER_ESTIMATOR_ALLOCATION",
            "thread_limit": 1,
            "maximum_fits": 144,
            "maximum_rows_per_fit": 20000,
            "between_fit_wall_budget_seconds": 600,
        },
    )
