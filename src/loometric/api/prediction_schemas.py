"""Closed hypothetical pre-shift input contract; no paths, outcomes or fit controls."""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ModelName = Literal["random_forest", "histogram_gradient_boosting", "grouped_mean"]
Count = Annotated[int, Field(ge=0, le=1_000_000)]


class SyntheticInputs(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    stage: str = Field(min_length=1, max_length=32, pattern=r"^[a-z_]+$")
    shift_kind: str = Field(min_length=1, max_length=32, pattern=r"^[a-z_]+$")
    weekday: int = Field(ge=0, le=6)
    planned_workers: int = Field(ge=0, le=100)
    skill_level: int = Field(ge=1, le=5)
    style_complexity: int = Field(ge=1, le=5)
    standard_worker_minutes_per_piece: float = Field(gt=0, le=100)
    planned_machine_available: bool
    available_minutes: int = Field(ge=0, le=480)
    planned_downtime_minutes: int = Field(ge=0, le=480)
    opening_wip_pieces: Count
    planned_release_pieces: Count
    order_quantity: int = Field(ge=1, le=1_000_000)

    @field_validator("standard_worker_minutes_per_piece", mode="before")
    @classmethod
    def exact_standard(cls, value):
        if type(value) not in (int, Decimal):
            raise ValueError("Explicit numeric standard required")
        decimal = Decimal(value)
        if not decimal.is_finite() or decimal.as_tuple().exponent < -2:
            raise ValueError("Use at most two decimal places")
        return float(decimal)

    @model_validator(mode="after")
    def consistent(self):
        if self.opening_wip_pieces + self.planned_release_pieces != self.order_quantity:
            raise ValueError("Opening WIP plus planned release must equal order quantity")
        if self.available_minutes + self.planned_downtime_minutes > 480:
            raise ValueError(
                "Available time already excludes planned downtime within a 480 minute shift"
            )
        return self


class SyntheticPredictionRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    schema_version: Literal[1]
    synthetic: Literal[True]
    prediction_context: Literal["HYPOTHETICAL_PRE_SHIFT"]
    models: list[ModelName] = Field(min_length=1, max_length=3)
    inputs: SyntheticInputs

    @model_validator(mode="before")
    @classmethod
    def strict_declarations(cls, value):
        if isinstance(value, dict) and (
            type(value.get("schema_version")) is not int or value.get("synthetic") is not True
        ):
            raise ValueError("Explicit version and synthetic declaration required")
        return value

    @field_validator("models")
    @classmethod
    def distinct_models(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Distinct model identifiers required")
        return value
