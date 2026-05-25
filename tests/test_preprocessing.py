import numpy as np
import pandas as pd
import pytest

from loometric.features import SOURCE_COLUMNS, build_features
from loometric.preprocessing import build_preprocessor, inspect_preprocessor


def test_metadata_uses_training_categories_and_preserves_unknown_counts(
    chronological_data: pd.DataFrame,
) -> None:
    features = build_features(chronological_data.loc[:, SOURCE_COLUMNS])
    preprocessing = build_preprocessor(("department", "team", "day_of_week", "day_of_month"))
    preprocessing.fit(features.iloc[:6])
    before = inspect_preprocessor(preprocessing, features.iloc[6:])
    assert before.training_categories["day_of_week"] == ("3", "4", "5")
    assert before.unknown_validation_categories["day_of_week"] == 8
    preprocessing.transform(features.iloc[6:])
    assert inspect_preprocessor(preprocessing, features.iloc[6:]) == before


def test_remainder_drops_outcomes_and_all_unselected_columns(
    chronological_data: pd.DataFrame,
) -> None:
    features = build_features(chronological_data.loc[:, SOURCE_COLUMNS])
    features["actual_productivity"] = chronological_data["actual_productivity"]
    preprocessing = build_preprocessor(("department", "team"))
    expected = preprocessing.fit_transform(features)
    features["actual_productivity"] = 999999
    features["day_of_month"] = -999999
    np.testing.assert_array_equal(preprocessing.transform(features), expected)
    assert not any("productivity" in column for column in preprocessing.get_feature_names_out())


def test_numeric_only_metadata_does_not_require_a_categorical_transformer(
    chronological_data: pd.DataFrame,
) -> None:
    features = build_features(chronological_data.loc[:, SOURCE_COLUMNS])
    preprocessing = build_preprocessor(("day_of_month",))
    preprocessing.fit(features)
    metadata = inspect_preprocessor(preprocessing, features)
    assert metadata.encoded_columns == ("numeric__day_of_month",)
    assert metadata.training_categories == metadata.unknown_validation_categories == {}


@pytest.mark.parametrize("columns", [("actual_productivity",), ("wip",), ("incentive",)])
def test_shared_preprocessor_rejects_restricted_features(columns: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match="eligible"):
        build_preprocessor(columns)
