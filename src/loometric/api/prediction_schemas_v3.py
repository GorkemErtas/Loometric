"""Additive v3 request; the original thirteen planned inputs and older schemas stay frozen."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from loometric.api.prediction_schemas import SyntheticPredictionRequest


class MatureHistory(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True, allow_inf_nan=False)
    recent_attainment_mean: float | None = Field(default=None, ge=0, le=3)
    recent_attainment_std: float | None = Field(default=None, ge=0, le=3)
    history_count: int = Field(default=0, ge=0, le=7)
    uncensored_history_count: int = Field(default=0, ge=0, le=7)
    history_age_hours: float | None = Field(default=None, ge=0, le=8760)

    @model_validator(mode="after")
    def consistent(self):
        if self.uncensored_history_count > self.history_count:
            raise ValueError("Uncensored count cannot exceed total history")
        available = self.uncensored_history_count >= 2
        if available != (
            self.recent_attainment_mean is not None and self.recent_attainment_std is not None
        ):
            raise ValueError("Mean/std require two uncensored mature reports")
        if not available and (
            self.recent_attainment_mean is not None or self.recent_attainment_std is not None
        ):
            raise ValueError("Insufficient history must stay explicitly missing")
        if (self.history_count > 0) != (self.history_age_hours is not None):
            raise ValueError("Age must describe an existing mature report")
        return self


class SyntheticPredictionRequestV3(SyntheticPredictionRequest):
    schema_version: Literal[3]
    models: list[
        Literal[
            "random_forest",
            "histogram_gradient_boosting",
            "grouped_mean",
            "rf_physics",
            "history_boost",
        ]
    ] = Field(min_length=1, max_length=5)
    history: MatureHistory = Field(default_factory=MatureHistory)
