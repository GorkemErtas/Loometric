"""Explicit evidence assertions; no invented operational freshness threshold."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from loometric.prediction.contracts import (
    ContractError,
    PredictionRequest,
    PredictionStatus,
    Warning,
    identifier,
    require_aware,
)


@dataclass(frozen=True)
class ReviewPolicy:
    policy_schema_version: int = 1
    source_id: str | None = None
    timing_evidence_reference: str | None = None
    maximum_snapshot_age_seconds: int | None = None
    freshness_evidence_reference: str | None = None
    unknown_team_action: str = "review"

    def __post_init__(self) -> None:
        if type(self.policy_schema_version) is not int or self.policy_schema_version != 1:
            raise ContractError("POLICY_SCHEMA_MISMATCH", "Supported policy schema version is 1.")
        for name in ("source_id", "timing_evidence_reference", "freshness_evidence_reference"):
            if (value := getattr(self, name)) is not None:
                identifier(value, name)
        if self.unknown_team_action not in ("review", "abstain"):
            raise ContractError("INVALID_POLICY", "unknown_team_action must be review or abstain.")
        limit = self.maximum_snapshot_age_seconds
        if limit is not None and (type(limit) is not int or limit <= 0):
            raise ContractError("INVALID_POLICY", "Snapshot age limit must be a positive integer.")
        if (limit is None) != (self.freshness_evidence_reference is None):
            raise ContractError(
                "INVALID_POLICY", "Freshness limit and evidence must be supplied together."
            )
        if (limit is not None or self.timing_evidence_reference) and not self.source_id:
            raise ContractError(
                "INVALID_POLICY", "Evidence assertions must be bound to a source_id."
            )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ReviewPolicy":
        if "policy_schema_version" not in payload or set(payload) - set(cls.__dataclass_fields__):
            raise ContractError(
                "INVALID_POLICY", "Missing policy version or unsupported policy fields."
            )
        return cls(**payload)


def assess_request(
    request: PredictionRequest,
    policy: ReviewPolicy,
    *,
    known_team: bool,
    as_of: datetime,
) -> tuple[PredictionStatus, tuple[Warning, ...]]:
    require_aware(as_of)
    blockers: list[Warning] = []
    reviews: list[Warning] = []
    if policy.source_id is not None and policy.source_id != request.source_id:
        blockers.append(
            Warning("SOURCE_MISMATCH", "Request source differs from the evidence policy.")
        )
    if request.source_snapshot_timestamp > as_of:
        blockers.append(
            Warning("FUTURE_SNAPSHOT", "Source snapshot is after the inference reference time.")
        )
    if as_of > request.prediction_cutoff:
        blockers.append(
            Warning("CUTOFF_PASSED", "Inference reference time is after prediction cutoff.")
        )
    if policy.timing_evidence_reference is None:
        reviews.append(
            Warning("TIMING_UNVERIFIED", "Pre-shift source availability remains unverified.")
        )
    if policy.maximum_snapshot_age_seconds is None:
        reviews.append(
            Warning("FRESHNESS_UNVERIFIED", "No evidence-backed freshness limit is configured.")
        )
    elif (
        as_of - request.source_snapshot_timestamp
    ).total_seconds() > policy.maximum_snapshot_age_seconds:
        blockers.append(
            Warning("STALE_SNAPSHOT", "Snapshot exceeds the configured evidence-backed limit.")
        )
    if not known_team:
        target = blockers if policy.unknown_team_action == "abstain" else reviews
        target.append(
            Warning("UNKNOWN_TEAM", "Team was absent from this artifact's training vocabulary.")
        )
    status = (
        PredictionStatus.ABSTAIN
        if blockers
        else PredictionStatus.REVIEW_REQUIRED
        if reviews
        else PredictionStatus.VALID_EXPERIMENTAL
    )
    return status, tuple(blockers + reviews)
