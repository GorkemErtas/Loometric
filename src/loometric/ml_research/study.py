"""Bounded original-training research; seal selection before spent validation diagnostics."""

import json
from dataclasses import dataclass
from time import perf_counter

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from loometric.execution import peak_working_set_bytes
from loometric.ml_research.diagnosis import (
    context_projection,
    historical_diagnosis,
    interaction_errors,
    matched_predictions,
)
from loometric.ml_research.features import DERIVED_UNITS
from loometric.ml_research.inspection import impurity_probe, permutation_probe
from loometric.ml_research.models import ResearchLedger, fit_research
from loometric.ml_research.protocol import ROOT, SOURCE_CONFIG_SHA, research_folds
from loometric.ml_research.risk import fit_support, residual_profile, risk_diagnostics
from loometric.ml_research.selection import change, choose_candidate, reported
from loometric.synthetic_ml.features import FEATURE_COLUMNS
from loometric.synthetic_ml.storage import digest
from loometric.synthetic_training.artifacts import environment, inspect_artifact
from loometric.synthetic_training.configuration import load_study
from loometric.synthetic_training.data import require
from loometric.synthetic_training.metrics import analyze, error_summary
from loometric.synthetic_training.selection import macro_profile
from loometric.synthetic_training.study import load_datasets

STUDY_DIRECTORY = ROOT / "data/processed/synthetic_training/exp-006-c"


def load_inputs(config: dict):
    from loometric.experimental_ml.artifacts import verified_bundle

    original_config = load_study(ROOT / "configs/synthetic_training_v1.json")
    require(digest(original_config) == SOURCE_CONFIG_SHA, "FROZEN_ORIGINAL_STUDY_REQUIRED")
    inspect_artifact(STUDY_DIRECTORY, expected_fingerprint=config["source_study_manifest_sha256"])
    original = json.loads((STUDY_DIRECTORY / "report.json").read_text(encoding="utf-8"))
    registry = json.loads(
        (ROOT / "src/loometric/experimental_ml/trusted_v1.json").read_text(encoding="utf-8")
    )
    served_manifest, served_metadata, _ = verified_bundle(
        ROOT / registry["directory"], registry["manifest_sha256"]
    )
    original["existing_m08c_forest_importance"] = {
        "manifest_sha256": registry["manifest_sha256"],
        "model_sha256": served_manifest["files"]["random_forest.joblib"],
        "importance": served_metadata["models"]["random_forest"]["global_feature_importance"],
        "scope": "EXISTING_BENCHMARK_FULL_TRAINING_MODEL_GLOBAL_IMPURITY",
        "executable_loaded": False,
    }
    require(original["configuration"] == original_config, "SOURCE_STUDY_CONFIGURATION_DRIFT")
    datasets = load_datasets(original_config, ROOT)
    contexts = {
        b["case_id"]: context_projection(ROOT / b["directory"], datasets[b["case_id"]])
        for b in original_config["datasets"]
    }
    with (STUDY_DIRECTORY / "validation-predictions.jsonl").open(encoding="utf-8") as source:
        rows = [json.loads(line) for line in source]
    return datasets, contexts, original, rows


@dataclass
class ResearchResult:
    report: dict
    historical: dict
    importance: dict
    ablations: dict
    oof_predictions: list[dict]
    diagnostic_predictions: list[dict]
    artifact_model: object
    measurements: dict


def diagnostic_thresholds(evaluations: dict, names: list[str], original_policy: dict) -> dict:
    # Apply frozen numerical thresholds to explicitly spent diagnostics. This
    # neither revises EXP-006 nor changes the already sealed OOF designation.
    baseline_cases = [c for c in evaluations if c.endswith("-baseline")]
    result = {}
    for name in names:
        score = macro_profile({c: evaluations[c][name]["overall"]["mae"] for c in baseline_cases})
        base = macro_profile(
            {c: evaluations[c]["grouped_mean"]["overall"]["mae"] for c in baseline_cases}
        )
        stage = max(
            change(report["mae"], models["grouped_mean"]["slices"]["stage"][s]["mae"])
            for models in evaluations.values()
            for s, report in models[name]["slices"]["stage"].items()
        )
        tails = {
            metric: max(
                change(models[name]["overall"][metric], models["grouped_mean"]["overall"][metric])
                for models in evaluations.values()
            )
            for metric in ("p95_positive_error", "worst_absolute_error")
        }
        stresses = {}
        stress_seeds = {}
        for scenario in ("disruption", "workload_surge"):
            cases = [c for c in evaluations if c.endswith("-" + scenario)]
            stresses[scenario] = change(
                float(np.mean([evaluations[c][name]["overall"]["mae"] for c in cases])),
                float(np.mean([evaluations[c]["grouped_mean"]["overall"]["mae"] for c in cases])),
            )
            stress_seeds.update(
                {
                    c: change(
                        evaluations[c][name]["overall"]["mae"],
                        evaluations[c]["grouped_mean"]["overall"]["mae"],
                    )
                    for c in cases
                }
            )
        result[name] = {
            "macro_mae": score,
            "macro_gain_vs_group_percent": reported(-change(score, base)),
            "maximum_stage_regression_percent": reported(stage),
            "tail_regression_percent": {k: reported(v) for k, v in tails.items()},
            "stress_macro_regression_percent": {k: reported(v) for k, v in stresses.items()},
            "stress_seed_regression_percent": {k: reported(v) for k, v in stress_seeds.items()},
            "frozen_numeric_checks": {
                "macro_gain": change(score, base)
                <= -original_policy["minimum_macro_improvement_percent"],
                "every_world_improves": all(
                    evaluations[c][name]["overall"]["mae"]
                    < evaluations[c]["grouped_mean"]["overall"]["mae"]
                    for c in baseline_cases
                ),
                "stage": stage <= original_policy["maximum_stage_regression_percent"],
                "positive_p95": tails["p95_positive_error"]
                <= original_policy["maximum_overprediction_p95_regression_percent"],
                "worst_error": tails["worst_absolute_error"]
                <= original_policy["maximum_worst_error_regression_percent"],
                "stress_macro": all(v <= 0 for v in stresses.values()),
                "stress_seed": max(stress_seeds.values())
                <= original_policy["maximum_stress_seed_regression_percent"],
            },
            "role": "SPENT_DIAGNOSTIC_NOT_SELECTION_OR_PROMOTION",
        }
    return result


def run_research(
    config: dict,
    datasets: dict,
    contexts: dict,
    original: dict,
    retained: list[dict],
    *,
    progress=None,
) -> ResearchResult:
    original_specs = {s["name"]: s for s in original["configuration"]["search"]}
    original_specs["grouped_mean"] = {"name": "grouped_mean", "family": "naive", "parameters": {}}
    specs = {name: original_specs[name] for name in config["references"]}
    specs.update({s["name"]: s for s in config["candidates"]})
    candidates = [s["name"] for s in config["candidates"]]
    cases = sorted(c for c in datasets if c.endswith("-baseline"))
    require(len(cases) == 4 and len(datasets) == 10, "FOUR_BASELINES_AND_SIX_STRESS_CASES_REQUIRED")
    historical = historical_diagnosis(datasets, contexts, retained, original, config)
    if progress:
        progress(
            {
                "stage": "historical_diagnosis_complete",
                "hidden_shift_pairs": historical["hidden_shift_pairs"],
            }
        )
    ledger = ResearchLedger(datasets, config["budget"])
    oof, fold_descriptions, temporal, importance, ablations, pooled = [], {}, {}, {}, {}, {}
    with threadpool_limits(limits=1):
        for case in cases:
            population = datasets[case].train
            collected = {name: [] for name in specs}
            ablation_predictions = {}
            temporal[case], importance[case], fold_descriptions[case] = (
                {name: [] for name in specs},
                {},
                [],
            )
            for fold in research_folds(population):
                ids = list(fold.evaluation_ids)
                fold_descriptions[case].append(
                    {
                        "name": fold.name,
                        "train_dates": list(fold.train_dates),
                        "evaluation_dates": list(fold.evaluation_dates),
                        "training_rows": len(fold.train_ids),
                        "evaluation_rows": len(ids),
                        "training_ids_sha256": digest(list(fold.train_ids)),
                        "evaluation_ids_sha256": digest(ids),
                    }
                )
                importance[case][fold.name] = {}
                for name, spec in specs.items():
                    model = fit_research(
                        spec, population, fold.train_ids, ledger, case, fold.name, config
                    )
                    predicted = ledger.predict(model, population.X.loc[ids], case, fold.name, name)
                    collected[name].append(predicted)
                    temporal[case][name].append(error_summary(population.y.loc[ids], predicted))
                    oof.extend(
                        {
                            "case": case,
                            "fold": fold.name,
                            "model": name,
                            "observation_id": oid,
                            "actual": float(population.y[oid]),
                            "prediction": float(predicted[oid]),
                            "stage": population.metadata.loc[oid, "stage"],
                        }
                        for oid in ids
                    )
                    if name in ("forest-12", "hist-31"):
                        importance[case][fold.name][name] = permutation_probe(
                            model,
                            population,
                            ids,
                            seed=config["resampling_seed"],
                            key=case + "|" + fold.name,
                            policy=config["permutation"],
                        )
                        if name == "forest-12":
                            importance[case][fold.name][name]["training_impurity_importance"] = (
                                impurity_probe(model)
                            )
                        for block, columns in config["ablations"].items():
                            altered = {**spec, "name": name + "/omit_" + block}
                            ablated = fit_research(
                                altered,
                                population,
                                fold.train_ids,
                                ledger,
                                case,
                                fold.name,
                                config,
                                omitted=tuple(columns),
                            )
                            prediction = ledger.predict(
                                ablated, population.X.loc[ids], case, fold.name, altered["name"]
                            )
                            ablation_predictions.setdefault(altered["name"], []).append(prediction)
                if progress:
                    progress(
                        {
                            "stage": "research_fold_complete",
                            "case": case,
                            "fold": fold.name,
                            "estimator_fits": len(ledger.fits),
                        }
                    )
            pooled[case] = {name: pd.concat(parts) for name, parts in collected.items()}
            ablations[case] = {}
            for name, parts in ablation_predictions.items():
                predicted = pd.concat(parts)
                raw_name = name.split("/")[0]
                ablations[case][name] = {
                    "omitted_columns": config["ablations"][name.split("omit_")[1]],
                    "metrics": error_summary(population.y.loc[predicted.index], predicted),
                    "reference_metrics": error_summary(
                        population.y.loc[predicted.index], pooled[case][raw_name]
                    ),
                    "matched_ids_sha256": digest(list(predicted.index)),
                    "selection_eligible": False,
                }
        training_evaluation = {
            case: {
                name: analyze(
                    datasets[case].train.y.loc[pred.index],
                    pred,
                    datasets[case].train.metadata.loc[pred.index],
                )
                for name, pred in predictions.items()
            }
            for case, predictions in pooled.items()
        }
        selection = choose_candidate(training_evaluation, temporal, candidates, config["selection"])
        sealed = digest(selection)
        if progress:
            progress(
                {
                    "stage": "selection_sealed_before_outer_diagnostics",
                    "selection": selection,
                    "selection_sha256": sealed,
                }
            )
        full_models, residuals, supports = {}, {}, {}
        for case in cases:
            population = datasets[case].train
            full_models[case] = {
                name: fit_research(
                    spec,
                    population,
                    population.X.index,
                    ledger,
                    case,
                    "full_original_training",
                    config,
                )
                for name, spec in specs.items()
            }
            supports[case] = fit_support(population.metadata)
            residuals[case] = {
                name: residual_profile(
                    population.y.loc[pred.index],
                    pred,
                    population.metadata.loc[pred.index],
                    config["risk"],
                )
                for name, pred in pooled[case].items()
            }
        diagnostics, outer, parity = {}, [], {}
        for case, data in datasets.items():
            base = (
                case
                if case.endswith("-baseline")
                else case.removesuffix("-disruption").removesuffix("-workload_surge") + "-baseline"
            )
            require(
                data.train.source_fingerprint == datasets[base].train.source_fingerprint,
                "NO_STRESS_REFIT_OR_TRAINING_DRIFT",
            )
            diagnostics[case] = {}
            for name, model in full_models[base].items():
                predicted = ledger.predict(
                    model, data.validation.X, case, "spent_outer_diagnostic", name
                )
                diagnostic = analyze(data.validation.y, predicted, data.validation.metadata)
                diagnostic["interactions"] = interaction_errors(data.validation, predicted)
                diagnostic["risk"] = risk_diagnostics(
                    data.validation,
                    predicted,
                    supports[base],
                    residuals[base][name],
                    config["risk"],
                )
                diagnostic["predictions_above_offered_work_ceiling"] = int(
                    (predicted - data.validation.metadata.planned_load_ratio > 1e-12).sum()
                )
                diagnostics[case][name] = diagnostic
                outer.extend(
                    {
                        "case": case,
                        "model": name,
                        "observation_id": oid,
                        "actual": float(data.validation.y[oid]),
                        "prediction": float(predicted[oid]),
                        "stage": data.validation.metadata.loc[oid, "stage"],
                    }
                    for oid in predicted.index
                )
                if name in config["references"]:
                    difference = float(
                        np.max(np.abs(predicted - matched_predictions(data, retained, case, name)))
                    )
                    require(difference <= 1e-12, "FROZEN_REFERENCE_PREDICTION_DRIFT")
                    parity[f"{case}|{name}"] = {
                        "rows": len(predicted),
                        "maximum_absolute_difference": difference,
                    }
            if progress:
                progress({"stage": "spent_diagnostic_complete", "case": case})
    require(digest(selection) == sealed, "DIAGNOSTICS_CHANGED_SEALED_SELECTION")
    artifact_name = selection["selected_candidate"] or selection["lowest_mae_candidate"]
    report = {
        "schema_version": 1,
        "experiment_id": "EXP-008",
        "policy_version": config["policy_version"],
        "configuration": config,
        "configuration_sha256": digest(config),
        "environment": environment(),
        "feature_definitions": DERIVED_UNITS,
        "existing_m08c_forest_importance": original.get("existing_m08c_forest_importance"),
        "raw_feature_order": list(FEATURE_COLUMNS),
        "engineered_feature_order": [*FEATURE_COLUMNS, *DERIVED_UNITS],
        "datasets": {
            case: {"provenance": data.provenance, "audit": data.audit}
            for case, data in datasets.items()
        },
        "folds": fold_descriptions,
        "temporal_fold_metrics": temporal,
        "original_training_oof": training_evaluation,
        "selection": selection,
        "sealed_selection_sha256": sealed,
        "spent_validation_diagnostics": diagnostics,
        "spent_validation_thresholds": diagnostic_thresholds(
            diagnostics, candidates, original["configuration"]["selection"]
        ),
        "frozen_reference_parity": parity,
        "fit_provenance": ledger.fits,
        "estimator_fits": len(ledger.fits),
        "residual_references": residuals,
        "artifact_model": artifact_name,
        "artifact_training_case": "benchmark-42-baseline",
        "artifact_status": "RESEARCH_CANDIDATE"
        if selection["selected_candidate"]
        else "UNSELECTED_LOWEST_OOF_MAE_CANDIDATE",
        "reserved_labels_decoded": False,
        "final_test_evaluated": False,
        "promotion_decision": "NO_ML_PROMOTION",
        "serving_artifacts_changed": False,
        "capacity_application_authorized": False,
        "validation_role": "REPEATEDLY_INSPECTED_DIAGNOSTIC_ONLY",
        "independent_confirmation_claim": False,
        "world_independence_claim": False,
    }
    return ResearchResult(
        report,
        historical,
        importance,
        ablations,
        oof,
        outer,
        full_models["benchmark-42-baseline"][artifact_name],
        {
            "elapsed_after_diagnosis_seconds": perf_counter() - ledger.started,
            "operations": ledger.measurements,
            "process_lifetime_peak_working_set_bytes": peak_working_set_bytes(),
            "memory_scope": "PROCESS_LIFETIME_NOT_PER_MODEL",
            "wall_budget_scope": "CHECKED_BETWEEN_FITS_NOT_OS_WATCHDOG",
        },
    )
