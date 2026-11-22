"""Version-1 offline assessment inputs, reports and deterministic identities."""

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from loometric.planning.loading import fields, parse_json
from loometric.planning.reporting import json_value
from loometric.prediction.contracts import (
    PredictionRequest,
    PredictionStatus,
    identifier,
    require_aware,
    timestamp,
)

SCHEMA_VERSION = 1
POLICY_VERSION = "m01-planning-audit-v1"
M01_GRAIN = "date_department_team_unverified"


class CompatibilityStatus(StrEnum):
    COMPATIBLE = "COMPATIBLE"
    CONDITIONAL = "CONDITIONAL"
    INCOMPATIBLE = "INCOMPATIBLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class GateStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NOT_ASSESSED = "NOT_ASSESSED"


class Gate(StrEnum):
    TARGET_UNITS = "target_units"
    FEATURE_TIMING = "feature_timing"
    DEPARTMENT_STAGE = "department_stage"
    TEAM_CREW = "team_crew"
    OBSERVATION_GRAIN = "observation_grain"
    DOMAIN_SHIFT = "domain_shift"
    MODEL_QUALITY = "model_quality"
    UNCERTAINTY = "uncertainty"
    ARTIFACT = "artifact_integrity"
    SUPPORTED_INPUTS = "supported_inputs"
    PREDICTION_RANGE = "prediction_range"
    OPERATIONAL_SAFETY = "operational_safety"


def sha256_value(value: object) -> str:
    """Typed audit identity, not an existing model or scheduling fingerprint."""
    return hashlib.sha256(
        json.dumps(
            json_value(value), sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def require_digest(value: str) -> None:
    if not isinstance(value, str) or re.fullmatch("[a-f0-9]{64}", value) is None:
        raise ValueError("A lowercase SHA-256 fingerprint is required.")


@dataclass(frozen=True)
class EvidenceReference:
    gate: Gate
    reference: str
    context_fingerprint: str

    def __post_init__(self) -> None:
        if not isinstance(self.gate, Gate):
            raise ValueError("Unsupported evidence gate.")
        identifier(self.reference, "evidence reference")
        require_digest(self.context_fingerprint)


@dataclass(frozen=True)
class AssessmentRequest:
    schema_version: int
    prediction_request: PredictionRequest
    predicted_productivity: Decimal | None
    prediction_status: PredictionStatus
    artifact_fingerprint: str
    model_configuration_fingerprint: str
    as_of: datetime
    observation_grain: str
    assignment_id: str
    order_id: str
    evidence_references: tuple[EvidenceReference, ...]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != SCHEMA_VERSION:
            raise ValueError("Only compatibility schema version 1 is supported.")
        if not isinstance(self.prediction_request, PredictionRequest) or not isinstance(
            self.prediction_status, PredictionStatus
        ):
            raise ValueError("Typed M01 prediction context is required.")
        if self.predicted_productivity is not None and not isinstance(
            self.predicted_productivity, Decimal
        ):
            raise ValueError(
                "Prediction must be a Decimal numeric token or null; no float coercion."
            )
        if (
            self.predicted_productivity is not None
            and self.predicted_productivity.is_finite()
            and (
                len(self.predicted_productivity.as_tuple().digits) > 128
                or abs(self.predicted_productivity.as_tuple().exponent) > 100
            )
        ):
            raise ValueError("Prediction exceeds the offline numeric bounds.")
        require_aware(self.as_of)
        for value in (self.artifact_fingerprint, self.model_configuration_fingerprint):
            require_digest(value)
        for value in (self.observation_grain, self.assignment_id, self.order_id):
            identifier(value, "assessment context")
        if type(self.evidence_references) is not tuple or not all(
            isinstance(e, EvidenceReference) for e in self.evidence_references
        ):
            raise ValueError("Evidence references must be an immutable typed collection.")
        if len({e.gate for e in self.evidence_references}) != len(self.evidence_references):
            raise ValueError("Only one evidence reference per gate is supported.")

    @classmethod
    def from_json(cls, source: str) -> "AssessmentRequest":
        raw = fields(bounded_json(source), tuple(cls.__dataclass_fields__))
        raw_prediction = raw["predicted_productivity"]
        if type(raw_prediction) is int:
            raw_prediction = Decimal(raw_prediction)
        if raw_prediction is not None and not isinstance(raw_prediction, Decimal):
            raise ValueError("Prediction requires a numeric token, not a string or boolean.")
        references = raw["evidence_references"]
        if not isinstance(references, list):
            raise ValueError("Evidence references require an explicit array.")
        return cls(
            **{
                **raw,
                "prediction_request": PredictionRequest.from_dict(raw["prediction_request"]),
                "prediction_status": PredictionStatus(raw["prediction_status"]),
                "predicted_productivity": raw_prediction,
                "as_of": timestamp(raw["as_of"]),
                "evidence_references": tuple(
                    EvidenceReference(
                        **{
                            **fields(e, tuple(EvidenceReference.__dataclass_fields__)),
                            "gate": Gate(e["gate"]),
                        }
                    )
                    for e in references
                ),
            }
        )


def bounded_json(source: str, max_bytes: int = 262144) -> dict[str, Any]:
    """Bound local JSON before the shared strict Decimal/unique-key decoder."""
    if len(source.encode("utf-8", errors="strict")) > max_bytes:
        raise ValueError("Local JSON exceeds the byte limit.")
    quoted, escaped, depth = False, False, 0
    for char in source:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > 24:
                raise ValueError("Local JSON exceeds the nesting limit.")
        elif char in "]}":
            depth -= 1
    value = parse_json(source)
    if not isinstance(value, dict):
        raise ValueError("A local JSON object is required.")
    pending, nodes = [value], 0
    while pending:
        item = pending.pop()
        nodes += 1
        if nodes > 100000:
            raise ValueError("Local JSON exceeds the node limit.")
        if isinstance(item, dict):
            if len(item) > 1024:
                raise ValueError("Local JSON record exceeds the item limit.")
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            if len(item) > 10000:
                raise ValueError("Local JSON array exceeds the item limit.")
            pending.extend(item)
        elif isinstance(item, str) and len(item) > 4096:
            raise ValueError("Local JSON text exceeds the string limit.")
        elif isinstance(item, Decimal) and (
            not item.is_finite()
            or len(item.as_tuple().digits) > 128
            or abs(item.as_tuple().exponent) > 100
        ):
            raise ValueError("Local JSON exceeds the Decimal bounds.")
    return value


@dataclass(frozen=True)
class ModelProfile:
    """Manifest metadata; the I/O boundary must verify the retained receipt and bytes.

    This profile is not a fitted model or evidence of operational validity.
    """

    artifact_fingerprint: str
    model_configuration_fingerprint: str
    dataset_sha256: str
    split_file_sha256: str
    pipeline_sha256: str
    training_end: date
    departments: tuple[str, ...]
    teams: tuple[str, ...]
    weekdays: tuple[str, ...]
    model_id: str = "B_RF-01"
    model_version: str = "m01-v1"

    def __post_init__(self) -> None:
        for name in (
            "artifact_fingerprint",
            "model_configuration_fingerprint",
            "dataset_sha256",
            "split_file_sha256",
            "pipeline_sha256",
        ):
            require_digest(getattr(self, name))
        if (
            self.model_id != "B_RF-01"
            or self.model_version != "m01-v1"
            or type(self.training_end) is not date
        ):
            raise ValueError("This policy assesses only M01 B_RF-01/m01-v1 metadata.")
        for values in (self.departments, self.teams, self.weekdays):
            if type(values) is not tuple or not values or len(set(values)) != len(values):
                raise ValueError("Training category vocabularies must be unique immutable tuples.")
            for value in values:
                identifier(value, "training category")
        if set(self.departments) != {"sewing", "finishing"}:
            raise ValueError("M01 supports sewing and finishing only.")


@dataclass(frozen=True)
class MappingCheck:
    name: str
    status: CompatibilityStatus
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ReadinessGate:
    gate: Gate
    status: GateStatus
    reason_codes: tuple[str, ...]
    evidence_references: tuple[str, ...] = ()


@dataclass(frozen=True)
class CompatibilityAssessment:
    status: CompatibilityStatus
    mappings: tuple[MappingCheck, ...]
    gates: tuple[ReadinessGate, ...]
    provenance: dict[str, str]
    declared_prediction: str | None
    schema_version: int = SCHEMA_VERSION
    policy_version: str = POLICY_VERSION
    integration_readiness: str = "NOT_READY"
    target_to_efficiency: str = "BLOCKED"
    capacity_application_authorized: bool = False
    converted_efficiency: None = None
    candidate_value_origin: str = "DECLARED_OFFLINE_CONTEXT_NOT_REEXECUTED"
    final_test_evaluated: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.schema_version) is not int
            or self.schema_version != SCHEMA_VERSION
            or self.policy_version != POLICY_VERSION
        ):
            raise ValueError("Unsupported compatibility result schema/policy.")
        if (
            self.status
            not in (CompatibilityStatus.INCOMPATIBLE, CompatibilityStatus.INSUFFICIENT_EVIDENCE)
            or self.integration_readiness != "NOT_READY"
            or self.target_to_efficiency != "BLOCKED"
            or self.capacity_application_authorized is not False
            or self.converted_efficiency is not None
            or self.final_test_evaluated is not False
        ):
            raise ValueError(
                "M07B cannot authorize conversion, readiness or final-test evaluation."
            )

    def to_dict(self) -> dict[str, Any]:
        return json_value(asdict(self))
