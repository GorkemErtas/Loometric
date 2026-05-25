"""Shared training-fitted categorical preprocessing for local regression experiments."""

from dataclasses import dataclass

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

from loometric.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES, validate_feature_names


def build_preprocessor(columns: tuple[str, ...]) -> ColumnTransformer:
    """Dense full one-hot encoding; unknown categories use zeros for that feature."""
    validate_feature_names(columns)
    categorical = [name for name in columns if name in CATEGORICAL_FEATURES]
    numeric = [name for name in columns if name in NUMERIC_FEATURES]
    transformers = []
    if categorical:
        transformers.append(
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", drop=None, sparse_output=False),
                categorical,
            )
        )
    if numeric:
        transformers.append(("numeric", "passthrough", numeric))
    return ColumnTransformer(transformers, remainder="drop")


@dataclass(frozen=True)
class FeatureMetadata:
    encoded_columns: tuple[str, ...]
    training_categories: dict[str, tuple[str, ...]]
    unknown_validation_categories: dict[str, int]


def inspect_preprocessor(
    fitted: ColumnTransformer, validation_features: pd.DataFrame
) -> FeatureMetadata:
    """Inspect learned training vocabularies without fitting or using outcome values."""
    encoder = fitted.named_transformers_.get("categorical")
    categories = (
        {
            str(column): tuple(str(value) for value in values)
            for column, values in zip(encoder.feature_names_in_, encoder.categories_, strict=True)
        }
        if encoder is not None
        else {}
    )
    return FeatureMetadata(
        encoded_columns=tuple(fitted.get_feature_names_out()),
        training_categories=categories,
        unknown_validation_categories={
            column: int((~validation_features[column].isin(values)).sum())
            for column, values in categories.items()
        },
    )
