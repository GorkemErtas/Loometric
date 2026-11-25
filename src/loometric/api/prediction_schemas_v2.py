"""Versioned experimental prediction request contract."""

from typing import Literal

from pydantic import Field

from loometric.api.prediction_schemas import (
    SyntheticPredictionRequest,
)

ModelNameV2 = Literal[
    "random_forest",
    "histogram_gradient_boosting",
    "grouped_mean",
    "rf_physics",
]


class SyntheticPredictionRequestV2(SyntheticPredictionRequest):
    schema_version: Literal[2]

    models: list[ModelNameV2] = Field(
        min_length=1,
        max_length=4,
    )
