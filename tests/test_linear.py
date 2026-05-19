import numpy as np
import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import OneHotEncoder

from loometric.data.schema import TARGET
from loometric.features import FEATURE_SETS, SOURCE_COLUMNS, build_features
from loometric.linear import build_linear_pipeline


def test_unknown_categories_are_finite_and_do_not_refit_encoder(
    chronological_data: pd.DataFrame,
) -> None:
    training = chronological_data.iloc[:8]
    features = build_features(training.loc[:, SOURCE_COLUMNS])
    model = build_linear_pipeline(FEATURE_SETS[-1][1])
    model.fit(features, training[TARGET])
    preprocessing = model.named_steps["preprocessing"]
    assert isinstance(preprocessing, ColumnTransformer)
    encoder = preprocessing.named_transformers_["categorical"]
    assert isinstance(encoder, OneHotEncoder)
    assert isinstance(model.named_steps["regression"], LinearRegression)
    categories = [values.copy() for values in encoder.categories_]
    unseen = features.iloc[[0]].copy()
    unseen["department"], unseen["team"], unseen["day_of_week"] = "new-department", "999", "2"
    assert np.isfinite(model.predict(unseen)).all()
    transformed = preprocessing.transform(unseen)
    assert np.equal(transformed[0, :-1], 0).all()
    assert transformed[0, -1] == 1
    for actual, expected in zip(encoder.categories_, categories, strict=True):
        np.testing.assert_array_equal(actual, expected)


def test_department_only_ols_reproduces_department_training_means(
    chronological_data: pd.DataFrame,
) -> None:
    features = build_features(chronological_data.loc[:, SOURCE_COLUMNS])
    model = build_linear_pipeline(("department",))
    model.fit(features, chronological_data[TARGET])
    predicted = model.predict(features)
    expected = chronological_data.groupby("department")[TARGET].transform("mean").to_numpy(float)
    np.testing.assert_allclose(predicted, expected, rtol=0, atol=1e-12)


def test_ols_is_deterministic_for_the_same_training_data(chronological_data: pd.DataFrame) -> None:
    features = build_features(chronological_data.loc[:, SOURCE_COLUMNS])
    models = [build_linear_pipeline(FEATURE_SETS[-1][1]) for _ in range(2)]
    for model in models:
        model.fit(features, chronological_data[TARGET])
    np.testing.assert_array_equal(models[0].predict(features), models[1].predict(features))
    np.testing.assert_array_equal(
        models[0].named_steps["regression"].coef_, models[1].named_steps["regression"].coef_
    )


def test_pipeline_rejects_ineligible_feature_selection() -> None:
    with pytest.raises(ValueError, match="eligible"):
        build_linear_pipeline(("department", "actual_productivity"))
