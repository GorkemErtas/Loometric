import copy
import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from loometric.api.prediction_schemas import SyntheticPredictionRequest
from loometric.experimental_ml.artifacts import load_trusted
from loometric.experimental_ml.constants import MODELS
from loometric.experimental_ml.inference import predict
from loometric.synthetic_ml.features import FEATURE_COLUMNS


@pytest.fixture
def body():
    return {
        "schema_version": 1,
        "synthetic": True,
        "prediction_context": "HYPOTHETICAL_PRE_SHIFT",
        "models": list(MODELS),
        "inputs": {
            "stage": "sewing",
            "shift_kind": "day",
            "weekday": 0,
            "planned_workers": 6,
            "skill_level": 3,
            "style_complexity": 3,
            "standard_worker_minutes_per_piece": 4,
            "planned_machine_available": True,
            "available_minutes": 420,
            "planned_downtime_minutes": 30,
            "opening_wip_pieces": 100,
            "planned_release_pieces": 500,
            "order_quantity": 600,
        },
    }


def test_actual_estimator_comparison_order_schema_and_no_fit(
    publication_fixture, body, monkeypatch
):
    metadata, models = load_trusted(
        publication_fixture["receipt"], directory=publication_fixture["directory"]
    )
    seen = []
    for name, model in models.items():
        monkeypatch.setattr(model, "fit", lambda *a, **k: pytest.fail("Inference trained a model"))
        original = model.predict

        def spy(X, original=original, name=name):
            assert tuple(X.columns) == FEATURE_COLUMNS
            seen.append((name, X.to_dict(orient="records")))
            return original(X)

        monkeypatch.setattr(model, "predict", spy)
    before = copy.deepcopy(body)
    result = predict(
        SyntheticPredictionRequest.model_validate(body),
        metadata,
        models,
        publication_fixture["receipt"],
    )
    assert body == before
    assert [r["model"] for r in result["results"]] == list(MODELS)
    assert len(seen) == 3 and seen[0][1] == seen[1][1] == seen[2][1]
    assert all(isinstance(r["prediction"], float) for r in result["results"])
    assert len(result["differences"]) == 3
    assert result["differences"][0]["left_minus_right"] == pytest.approx(
        result["results"][0]["prediction"] - result["results"][1]["prediction"]
    )
    assert result["capacity_application_authorized"] is False
    assert all(r["descriptive_band"]["coverage_guarantee"] is False for r in result["results"])


@pytest.mark.parametrize(
    "updates,reason",
    [
        ({"planned_workers": 0}, "ZERO_PLANNED_CAPACITY_UNDEFINED_TARGET"),
        ({"available_minutes": 0}, "ZERO_PLANNED_CAPACITY_UNDEFINED_TARGET"),
        ({"planned_machine_available": False}, "ZERO_PLANNED_CAPACITY_UNDEFINED_TARGET"),
        ({"stage": "unknown"}, "UNSUPPORTED_CATEGORICAL_INPUT"),
        ({"shift_kind": "unknown"}, "UNSUPPORTED_CATEGORICAL_INPUT"),
        ({"weekday": 6}, "UNSUPPORTED_CATEGORICAL_INPUT"),
    ],
)
def test_abstention_never_executes_estimators(
    publication_fixture, body, monkeypatch, updates, reason
):
    metadata, models = load_trusted(
        publication_fixture["receipt"], directory=publication_fixture["directory"]
    )
    for model in models.values():
        monkeypatch.setattr(
            model, "predict", lambda *a, **k: pytest.fail("Abstained input reached estimator")
        )
    body["inputs"].update(updates)
    result = predict(SyntheticPredictionRequest.model_validate(body), metadata, models, "receipt")
    assert all(
        r["prediction"] is None
        and r["descriptive_band"] is None
        and reason in r["support"]["reason_codes"]
        for r in result["results"]
    )
    assert all(r["left_minus_right"] is None for r in result["differences"])


def test_review_and_above_one_predictions_are_not_clipped(publication_fixture, body, monkeypatch):
    metadata, models = load_trusted(
        publication_fixture["receipt"], directory=publication_fixture["directory"]
    )
    body["inputs"]["planned_workers"] = 30
    monkeypatch.setattr(models["random_forest"], "predict", lambda X: [1.2])
    body["models"] = ["random_forest"]
    result = predict(SyntheticPredictionRequest.model_validate(body), metadata, models, "receipt")[
        "results"
    ][0]
    assert result["prediction"] == 1.2
    assert result["support"]["status"] == "REVIEW_REQUIRED"
    assert "OUTSIDE_TRAINING_SUPPORT:planned_workers" in result["support"]["reason_codes"]
    assert result["descriptive_band"]["upper"] > 1.2


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1, 3.1])
def test_unsupported_estimator_output_abstains(publication_fixture, body, monkeypatch, value):
    metadata, models = load_trusted(
        publication_fixture["receipt"], directory=publication_fixture["directory"]
    )
    monkeypatch.setattr(models["random_forest"], "predict", lambda X: [value])
    body["models"] = ["random_forest"]
    r = predict(SyntheticPredictionRequest.model_validate(body), metadata, models, "receipt")[
        "results"
    ][0]
    assert r["prediction"] is None and r["support"]["status"] == "ABSTAIN"


@pytest.mark.parametrize(
    "field,value",
    [
        ("planned_workers", True),
        ("planned_workers", 1.5),
        ("planned_workers", "6"),
        ("skill_level", 0),
        ("style_complexity", 6),
        ("weekday", 7),
        ("standard_worker_minutes_per_piece", "4"),
        ("standard_worker_minutes_per_piece", Decimal("4.001")),
        ("standard_worker_minutes_per_piece", Decimal("NaN")),
        ("planned_machine_available", 1),
        ("opening_wip_pieces", -1),
        ("order_quantity", 601),
        ("available_minutes", 470),
    ],
)
def test_invalid_or_inconsistent_inputs_rejected(body, field, value):
    body["inputs"][field] = value
    with pytest.raises(ValidationError):
        SyntheticPredictionRequest.model_validate(body)


@pytest.mark.parametrize(
    "updates",
    [
        {"schema_version": True},
        {"synthetic": 1},
        {"synthetic": False},
        {"prediction_context": "MEASURED_FACTORY"},
        {"models": []},
        {"models": ["random_forest", "random_forest"]},
        {"models": ["ridge"]},
        {"path": "untrusted.joblib"},
        {"receipt": "a" * 64},
        {"train": True},
    ],
)
def test_closed_version_and_model_envelope(body, updates):
    body.update(updates)
    with pytest.raises(ValidationError):
        SyntheticPredictionRequest.model_validate(body)


def test_missing_extra_and_wrong_order_inputs(body):
    body["inputs"]["actual_productivity"] = 0.8
    with pytest.raises(ValidationError):
        SyntheticPredictionRequest.model_validate(body)
    del body["inputs"]["actual_productivity"]
    del body["inputs"]["planned_workers"]
    with pytest.raises(ValidationError):
        SyntheticPredictionRequest.model_validate(body)


def test_wire_decimal_and_model_order(body):
    body["inputs"]["standard_worker_minutes_per_piece"] = 4.25
    decoded = json.loads(json.dumps(body), parse_float=Decimal)
    contract = SyntheticPredictionRequest.model_validate(decoded)
    assert contract.inputs.standard_worker_minutes_per_piece == 4.25
    assert contract.models == list(MODELS)
