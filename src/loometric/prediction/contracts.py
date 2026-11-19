"""Strict versioned wire contracts, independent of pandas and model persistence."""

import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Any

INPUT_SCHEMA_VERSION = 1


class ContractError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def identifier(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ContractError("INVALID_PROVENANCE", f"{name} must be a nonblank canonical string.")
    if any(ord(character) < 32 for character in value):
        raise ContractError("INVALID_PROVENANCE", f"{name} cannot contain control characters.")
    return value


def timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?"
        r"(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])",
        value,
    ):
        raise ContractError("INVALID_TIMESTAMP", "Use an ISO timestamp with seconds and timezone.")
    try:
        parsed = datetime.fromisoformat(value)
        require_aware(parsed)
        return parsed
    except ValueError as exc:
        raise ContractError("INVALID_TIMESTAMP", "Invalid timezone-aware timestamp.") from exc


def require_aware(value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ContractError("INVALID_TIMESTAMP", "Timestamp must be timezone-aware.")


def read_json(text: str) -> dict[str, Any]:
    """Reject duplicate keys and nonstandard NaN/Infinity rather than losing information."""

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value: str) -> None:
        raise ValueError(f"Invalid JSON constant: {value}")

    try:
        payload = json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant)
        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON object.")
        return payload
    except ValueError as exc:
        raise ContractError("INVALID_JSON", str(exc)) from exc


@dataclass(frozen=True)
class PredictionRequest:
    input_schema_version: int
    scheduled_date: date
    department: str
    team: str
    prediction_cutoff: datetime
    source_snapshot_timestamp: datetime
    source_id: str
    shift_id: str | None = None

    def __post_init__(self) -> None:
        if type(self.input_schema_version) is not int or self.input_schema_version != 1:
            raise ContractError("SCHEMA_MISMATCH", "Supported input schema version is 1.")
        if type(self.scheduled_date) is not date:
            raise ContractError("INVALID_DATE", "Scheduled date must be a calendar date.")
        if self.department not in ("finishing", "sewing"):
            raise ContractError("INVALID_DEPARTMENT", "Department must be finishing or sewing.")
        if not isinstance(self.team, str) or not re.fullmatch(r"[1-9][0-9]{0,8}", self.team):
            raise ContractError(
                "INVALID_TEAM", "Team must be a canonical positive ID (1-9 digits)."
            )
        identifier(self.source_id, "source_id")
        if self.shift_id is not None:
            identifier(self.shift_id, "shift_id")
        require_aware(self.prediction_cutoff)
        require_aware(self.source_snapshot_timestamp)
        if self.source_snapshot_timestamp > self.prediction_cutoff:
            raise ContractError(
                "SNAPSHOT_AFTER_CUTOFF", "Source snapshot is after prediction cutoff."
            )
        if self.prediction_cutoff.date() > self.scheduled_date:
            raise ContractError("INVALID_CUTOFF", "Cutoff date is after the scheduled date.")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PredictionRequest":
        expected = set(cls.__dataclass_fields__)
        if set(payload) - expected or expected - {"shift_id"} - set(payload):
            raise ContractError("INVALID_FIELDS", "Request has missing or unsupported fields.")
        raw_date = payload["scheduled_date"]
        if not isinstance(raw_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date):
            raise ContractError("INVALID_DATE", "Use YYYY-MM-DD for scheduled_date.")
        try:
            scheduled = date.fromisoformat(raw_date)
        except ValueError as exc:
            raise ContractError("INVALID_DATE", "Invalid scheduled date.") from exc
        return cls(
            **{
                **payload,
                "scheduled_date": scheduled,
                "prediction_cutoff": timestamp(payload["prediction_cutoff"]),
                "source_snapshot_timestamp": timestamp(payload["source_snapshot_timestamp"]),
            }
        )

    def provenance(self) -> dict[str, str | None]:
        return {
            "source_id": self.source_id,
            "source_snapshot_timestamp": self.source_snapshot_timestamp.isoformat(),
            "prediction_cutoff": self.prediction_cutoff.isoformat(),
            "scheduled_date": self.scheduled_date.isoformat(),
            "department": self.department,
            "team": self.team,
            "shift_id": self.shift_id,
        }


class PredictionStatus(StrEnum):
    VALID_EXPERIMENTAL = "VALID_EXPERIMENTAL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    ABSTAIN = "ABSTAIN"


@dataclass(frozen=True)
class Warning:
    code: str
    message: str


@dataclass(frozen=True)
class PredictionResult:
    status: PredictionStatus
    predicted_productivity: float | None
    baseline_prediction: float | None
    model_id: str | None
    model_version: str | None
    input_schema_version: int
    model_configuration_fingerprint: str | None
    artifact_fingerprint: str | None
    prediction_timestamp: str
    as_of_timestamp: str
    execution_mode: str
    source_provenance: dict[str, str | None] | None
    validation_warnings: tuple[Warning, ...]
    experimental: bool = True
    human_review_required: bool = True
    decision_eligibility: str = "NOT_ELIGIBLE_FOR_AUTOMATED_DECISIONS"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
