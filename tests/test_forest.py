from dataclasses import asdict

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestRegressor

from loometric.data.schema import TARGET
from loometric.features import SOURCE_COLUMNS, build_features
from loometric.forest import (
    FOREST_CONFIGURATIONS,
    FOREST_FEATURE_SETS,
    build_forest_pipeline,
    summarize_importance,
)
from loometric.leakage import FEATURE_POLICIES
from loometric.preprocessing import build_preprocessor, inspect_preprocessor


def test_exact_predeclared_six_candidate_plan() -> None:
    assert FOREST_FEATURE_SETS == (
        ("A", ("department", "team")),
        ("B", ("department", "team", "day_of_week", "day_of_month")),
    )
    assert [asdict(profile) for profile in FOREST_CONFIGURATIONS] == [
        {"name": "RF-01", "n_estimators": 100, "max_depth": 3, "min_samples_leaf": 20},
        {"name": "RF-02", "n_estimators": 200, "max_depth": 6, "min_samples_leaf": 10},
        {"name": "RF-03", "n_estimators": 300, "max_depth": None, "min_samples_leaf": 2},
    ]


@pytest.mark.parametrize("number", range(3))
def test_forest_configuration_and_deterministic_settings(number: int) -> None:
    profile = FOREST_CONFIGURATIONS[number]
    pipeline = build_forest_pipeline(FOREST_FEATURE_SETS[0][1], profile)
    model = pipeline.named_steps["regression"]
    assert isinstance(model, RandomForestRegressor)
    parameters = model.get_params()
    for name in ("n_estimators", "max_depth", "min_samples_leaf"):
        assert parameters[name] == getattr(profile, name)
    assert {
        name: parameters[name]
        for name in (
            "random_state",
            "n_jobs",
            "criterion",
            "bootstrap",
            "max_features",
            "min_samples_split",
            "max_samples",
            "oob_score",
            "warm_start",
        )
    } == {
        "random_state": 42,
        "n_jobs": 1,
        "criterion": "squared_error",
        "bootstrap": True,
        "max_features": 1.0,
        "min_samples_split": 2,
        "max_samples": None,
        "oob_score": False,
        "warm_start": False,
    }


@pytest.mark.parametrize(
    "column", [policy.name for policy in FEATURE_POLICIES if policy.availability != "pre_shift"]
)
def test_forest_cannot_select_conditional_realized_or_target_inputs(column: str) -> None:
    with pytest.raises(ValueError, match="eligible"):
        build_forest_pipeline(("department", column), FOREST_CONFIGURATIONS[0])


def test_seeded_forest_predictions_and_importance_are_reproducible(
    chronological_data: pd.DataFrame,
) -> None:
    features = build_features(chronological_data.loc[:, SOURCE_COLUMNS])
    models = [
        build_forest_pipeline(FOREST_FEATURE_SETS[1][1], FOREST_CONFIGURATIONS[2]) for _ in range(2)
    ]
    for model in models:
        model.fit(features, chronological_data[TARGET])
    np.testing.assert_array_equal(models[0].predict(features), models[1].predict(features))
    np.testing.assert_array_equal(
        models[0].named_steps["regression"].feature_importances_,
        models[1].named_steps["regression"].feature_importances_,
    )
    for first, second in zip(
        models[0].named_steps["regression"].estimators_,
        models[1].named_steps["regression"].estimators_,
        strict=True,
    ):
        assert first.random_state == second.random_state


def test_unknown_categories_predict_without_learning_from_inference(
    chronological_data: pd.DataFrame,
) -> None:
    features = build_features(chronological_data.loc[:, SOURCE_COLUMNS])
    model = build_forest_pipeline(FOREST_FEATURE_SETS[1][1], FOREST_CONFIGURATIONS[0])
    model.fit(features.iloc[:6], chronological_data[TARGET].iloc[:6])
    preprocessing = model.named_steps["preprocessing"]
    original = inspect_preprocessor(preprocessing, features)
    unknown = features.iloc[[0]].copy()
    unknown["department"], unknown["team"], unknown["day_of_week"] = "new", "999", "0"
    assert np.isfinite(model.predict(unknown)).all()
    assert inspect_preprocessor(preprocessing, features) == original
    assert np.equal(preprocessing.transform(unknown)[0, :-1], 0).all()


def test_grouped_importance_matches_known_encoded_column_sums(
    chronological_data: pd.DataFrame,
) -> None:
    features = build_features(chronological_data.loc[:, SOURCE_COLUMNS])
    preprocessing = build_preprocessor(FOREST_FEATURE_SETS[1][1]).fit(features.iloc[:6])
    # Two departments, two team IDs, three weekdays, one numeric day = eight columns.
    weights = np.arange(1, 9) / 36
    importance = summarize_importance(preprocessing, weights)
    assert importance.grouped == pytest.approx(
        {"department": 3 / 36, "team": 7 / 36, "day_of_week": 18 / 36, "day_of_month": 8 / 36}
    )
    assert sum(importance.encoded.values()) == pytest.approx(1)
    assert sum(importance.grouped.values()) == pytest.approx(1)
    assert len(importance.encoded) == 8
    assert all(
        value == 0 for value in summarize_importance(preprocessing, [0] * 8).grouped.values()
    )


@pytest.mark.parametrize("kind", ["width", "negative", "nonfinite"])
def test_invalid_importance_is_rejected(chronological_data: pd.DataFrame, kind: str) -> None:
    features = build_features(chronological_data.loc[:, SOURCE_COLUMNS])
    preprocessing = build_preprocessor(("department",)).fit(features)
    values = [0.5] if kind == "width" else [-0.5, 1.5] if kind == "negative" else [float("nan"), 1]
    with pytest.raises(ValueError, match="Importance"):
        summarize_importance(preprocessing, values)
