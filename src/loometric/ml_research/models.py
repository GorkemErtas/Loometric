"""Fixed research estimators and explicit train-only fit accounting."""

from dataclasses import dataclass
from time import perf_counter

import numpy as np
import pandas as pd

from loometric.ml_research.features import DERIVED_UNITS, STAGES, PlannedFeatures
from loometric.synthetic_ml.storage import digest
from loometric.synthetic_training.data import require
from loometric.synthetic_training.models import MeanModel, SchemaGuard, build_model, validate_matrix


class ResidualGuard(SchemaGuard):
    """A signed residual is a distinct training response, not a relabeled target."""

    def fit(self, X, y=None):
        super().fit(X)
        require(
            y is not None and X.index.equals(y.index) and np.isfinite(y).all(),
            "ALIGNED_FINITE_RESIDUALS_REQUIRED",
        )
        return self


def pipeline(spec: dict, seed: int, *, engineered: bool, omitted: tuple = (), residual=False):
    model = build_model(spec, seed)
    if isinstance(model, MeanModel):
        return model
    if residual:
        model.set_params(schema=ResidualGuard())
    if engineered:
        model.steps.insert(1, ("planned_features", PlannedFeatures()))
    preprocess = model.named_steps["preprocess"]
    preprocess.transformers = [
        (
            name,
            transformer,
            [c for c in columns if c not in omitted]
            + (list(DERIVED_UNITS) if engineered and name == "numeric" else []),
        )
        for name, transformer, columns in preprocess.transformers
    ]
    return model


@dataclass
class ResidualPredictor:
    baseline: object
    residual: object

    def predict(self, X):
        return self.baseline.predict(X) + self.residual.predict(X)


@dataclass
class StagePredictor:
    global_model: object
    stage_models: dict
    weights: dict

    def predict(self, X):
        values = pd.Series(self.global_model.predict(X), index=X.index)
        for stage, model in self.stage_models.items():
            ids = X.index[X.stage.eq(stage)]
            if len(ids):
                weight = self.weights[stage]
                values.loc[ids] = (
                    weight * model.predict(X.loc[ids]) + (1 - weight) * values.loc[ids]
                )
        return values.to_numpy()


class ResearchLedger:
    def __init__(self, datasets: dict, budget: dict):
        self.populations = {
            case: data.train for case, data in datasets.items() if case.endswith("-baseline")
        }
        self.budget = budget
        require(
            budget["maximum_estimator_fits"] <= 300
            and budget["maximum_rows_per_fit"] <= 20000
            and budget["between_fit_wall_seconds"] <= 1200,
            "BOUNDED_RESEARCH_BUDGET_REQUIRED",
        )
        self.started = perf_counter()
        self.fits, self.measurements = [], []

    def fit(self, model, X, y, case: str, scope: str, name: str, response="original_target"):
        population = self.populations[case]
        require(
            len(self.fits) < self.budget["maximum_estimator_fits"]
            and 0 < len(X) <= self.budget["maximum_rows_per_fit"],
            "RESEARCH_FIT_BOUND",
        )
        require(
            perf_counter() - self.started <= self.budget["between_fit_wall_seconds"],
            "RESEARCH_BETWEEN_FIT_WALL_BOUND",
        )
        require(
            set(X.index) <= set(population.X.index)
            and X.equals(population.X.loc[X.index])
            and X.index.equals(y.index)
            and np.isfinite(y).all(),
            "ORIGINAL_TRAINING_FEATURES_ONLY",
        )
        require(
            response in ("original_target", "training_baseline_residual"),
            "DECLARED_RESPONSE_REQUIRED",
        )
        if response == "original_target":
            require(y.equals(population.y.loc[X.index]), "ORIGINAL_TRAINING_LABELS_ONLY")
        before = digest({"X": X.to_dict(orient="split"), "y": list(y)})
        start = perf_counter()
        model.fit(X, y)
        seconds = perf_counter() - start
        require(
            before == digest({"X": X.to_dict(orient="split"), "y": list(y)}),
            "RESEARCH_FIT_MUTATION",
        )
        self.fits.append(
            {
                "case": case,
                "scope": scope,
                "model": name,
                "response": response,
                "rows": len(X),
                "ids_sha256": digest(list(X.index)),
                "fit_payload_sha256": before,
                "first_date": min(population.metadata.loc[X.index, "start_date"]).isoformat(),
                "last_date": max(population.metadata.loc[X.index, "start_date"]).isoformat(),
            }
        )
        self.measurements.append(
            {
                "case": case,
                "scope": scope,
                "model": name,
                "operation": "fit",
                "seconds": seconds,
                "rows": len(X),
            }
        )
        return model

    def predict(self, model, X, case, scope, name):
        start = perf_counter()
        result = pd.Series(model.predict(X), index=X.index, dtype="float64")
        require(np.isfinite(result).all(), "FINITE_RESEARCH_PREDICTIONS_REQUIRED")
        self.measurements.append(
            {
                "case": case,
                "scope": scope,
                "model": name,
                "operation": "predict",
                "seconds": perf_counter() - start,
                "rows": len(X),
            }
        )
        return result


def fit_research(
    spec: dict,
    population,
    ids,
    ledger: ResearchLedger,
    case: str,
    scope: str,
    config: dict,
    omitted: tuple = (),
):
    X, y = population.X.loc[list(ids)], population.y.loc[list(ids)]
    validate_matrix(X)
    name, architecture = spec["name"], spec.get("architecture", "raw")
    engineered = architecture != "raw"
    seed = config["model_seed"]
    if architecture == "baseline_residual":
        baseline = ledger.fit(MeanModel("grouped_mean"), X, y, case, scope, name + "/baseline")
        residual = y - baseline.predict(X)
        model = ledger.fit(
            pipeline(spec, seed, engineered=True, residual=True),
            X,
            residual,
            case,
            scope,
            name + "/residual",
            "training_baseline_residual",
        )
        return ResidualPredictor(baseline, model)
    global_model = ledger.fit(
        pipeline(spec, seed, engineered=engineered, omitted=omitted), X, y, case, scope, name
    )
    if architecture != "stage_shrunk":
        return global_model
    stages, weights = {}, {}
    policy = config["stage_model"]
    for stage in STAGES:
        index = X.index[X.stage.eq(stage)]
        if (
            len(index) >= policy["minimum_training_rows"]
            and population.metadata.loc[index, "start_date"].nunique()
            >= policy["minimum_training_dates"]
        ):
            stages[stage] = ledger.fit(
                pipeline(spec, seed, engineered=True),
                X.loc[index],
                y.loc[index],
                case,
                scope,
                name + "/" + stage,
            )
            weights[stage] = len(index) / (len(index) + policy["shrinkage_rows"])
    return StagePredictor(global_model, stages, weights)
