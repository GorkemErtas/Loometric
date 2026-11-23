import copy
from types import SimpleNamespace

import numpy as np
import pytest
from threadpoolctl import threadpool_limits

from loometric.ml_research.inspection import paired_errors, permutation_probe
from loometric.ml_research.models import (
    ResearchLedger,
    ResidualPredictor,
    StagePredictor,
    fit_research,
)
from loometric.ml_research.protocol import load_protocol
from loometric.ml_research.risk import fit_support, residual_profile, risk_diagnostics, risk_flags


def small_config():
    config = copy.deepcopy(load_protocol())
    for spec in config["candidates"]:
        spec["parameters"]["n_estimators" if spec["family"] == "forest" else "max_iter"] = 3
    return config


@pytest.mark.parametrize("number", range(6))
def test_actual_candidate_predictions_reproduce_and_fits_use_original_rows(
    research_population, number
):
    population, config = research_population, small_config()
    case = "benchmark-42-baseline"
    datasets = {case: SimpleNamespace(train=population)}
    first, second = (
        ResearchLedger(datasets, config["budget"]),
        ResearchLedger(datasets, config["budget"]),
    )
    spec = config["candidates"][number]
    with threadpool_limits(limits=1):
        a = fit_research(spec, population, population.X.index, first, case, "private", config)
        b = fit_research(spec, population, population.X.index, second, case, "private", config)
        assert np.array_equal(a.predict(population.X), b.predict(population.X))
    assert first.fits == second.fits
    if spec["architecture"] == "baseline_residual":
        assert isinstance(a, ResidualPredictor)
        assert first.fits[1]["response"] == "training_baseline_residual"
    if spec["architecture"] == "stage_shrunk":
        assert isinstance(a, StagePredictor) and a.stage_models == {}


def test_stage_partial_pooling_requires_support_and_has_declared_weights(research_population):
    config = small_config()
    config["stage_model"]["minimum_training_rows"] = 50
    case = "benchmark-42-baseline"
    ledger = ResearchLedger({case: SimpleNamespace(train=research_population)}, config["budget"])
    spec = config["candidates"][-1]
    with threadpool_limits(limits=1):
        model = fit_research(
            spec, research_population, research_population.X.index, ledger, case, "private", config
        )
        assert len(model.stage_models) == 5 and len(ledger.fits) == 6
        assert model.weights["packing"] == 60 / 260
        X = research_population.X.loc[research_population.X.stage.eq("packing")]
        expected = model.weights["packing"] * model.stage_models["packing"].predict(X) + (
            1 - model.weights["packing"]
        ) * model.global_model.predict(X)
        assert np.array_equal(model.predict(X), expected)


def test_ablation_excludes_columns_without_imputation_or_row_changes(research_population):
    config = small_config()
    case = "benchmark-42-baseline"
    ledger = ResearchLedger({case: SimpleNamespace(train=research_population)}, config["budget"])
    spec = {
        "name": "private-forest-ablation",
        "family": "forest",
        "parameters": {"n_estimators": 3, "max_depth": 12, "min_samples_leaf": 5},
    }
    model = fit_research(
        spec,
        research_population,
        research_population.X.index,
        ledger,
        case,
        "private",
        config,
        omitted=("opening_wip_pieces", "planned_release_pieces"),
    )
    names = model.named_steps["preprocess"].get_feature_names_out()
    assert not any("opening_wip" in name or "planned_release" in name for name in names)
    assert any("order_quantity" in name for name in names)
    assert ledger.fits[0]["rows"] == 300
    bad = research_population.X.copy()
    bad.index = ["validation-" + name for name in bad.index]
    with pytest.raises(ValueError, match="ORIGINAL_TRAINING"):
        ledger.fit(model, bad, research_population.y, case, "bad", "bad")


def test_permutation_is_matched_reproducible_and_marks_incoherent_inputs(research_population):
    population = research_population
    X = population.X
    X["opening_wip_pieces"] += np.arange(len(X)) % 5
    X["planned_release_pieces"] = X.order_quantity - X.opening_wip_pieces

    class Model:
        def predict(self, frame):
            return frame.opening_wip_pieces.to_numpy() / 200

    policy = {"max_evaluation_rows": 80, "repeats": 3}
    first = permutation_probe(Model(), population, X.index, seed=42, key="private", policy=policy)
    assert first == permutation_probe(
        Model(), population, X.index, seed=42, key="private", policy=policy
    )
    assert len(first["groups"]) == 15 and first["rows"] == 80
    assert first["groups"]["opening_wip_pieces"]["known_physical_inconsistency_fraction"] > 0
    assert first["groups"]["joint_demand"]["known_physical_inconsistency_fraction"] == 0
    assert first["groups"]["weekday"]["changed_row_fraction"] == 0
    assert first["groups"]["weekday"]["identifiable_under_block_scheme"] is False


def test_paired_date_resampling_counts_and_alignment(research_population):
    p = research_population
    result = paired_errors(p.y, p.y + 0.1, p.y + 0.05, p.metadata, seed=42, repeats=100)
    assert result["samples"] == 300 and result["dates"] == 30
    assert result["mae_difference_left_minus_right"] == pytest.approx(0.05)
    assert result["descriptive_date_bootstrap_interval"] == pytest.approx([0.05, 0.05])
    assert result == paired_errors(p.y, p.y + 0.1, p.y + 0.05, p.metadata, seed=42, repeats=100)
    with pytest.raises(ValueError, match="MATCHED"):
        paired_errors(p.y, p.y.iloc[::-1], p.y, p.metadata, seed=42)


def test_feature_only_risk_cannot_identify_hidden_target_change(research_population):
    p, policy = research_population, load_protocol()["risk"]
    profile = fit_support(p.metadata)
    before = risk_flags(p.metadata, profile, policy)
    p.y[:] = p.y * 0.8
    assert before.equals(risk_flags(p.metadata, profile, policy))
    prediction = p.y + 0.1
    residuals = residual_profile(p.y, prediction, p.metadata, policy)
    result = risk_diagnostics(p, prediction, profile, residuals, policy)
    assert result["coverage_guarantee"] is False and result["selection_reused_folds"] is True
    assert result["hidden_shift_detection_claim"] is False
    assert all(row["radius"] > 0 for row in residuals["stage_load_radii"].values())
