"""Synthetic contract cases; evidence values here are test fixtures, not operating policy."""

from datetime import datetime

import pytest

from loometric.prediction.contracts import ContractError, PredictionRequest, read_json
from loometric.prediction.policy import ReviewPolicy, assess_request


@pytest.fixture
def request_payload():
    return {
        "input_schema_version": 1,
        "scheduled_date": "2030-01-02",
        "department": "sewing",
        "team": "1",
        "prediction_cutoff": "2030-01-02T07:00:00+03:00",
        "source_snapshot_timestamp": "2030-01-02T06:30:00+03:00",
        "source_id": "synthetic:contract-test",
    }


def test_valid_contract_and_default_review(request_payload):
    request = PredictionRequest.from_dict(request_payload)
    assert request.provenance()["shift_id"] is None
    status, warnings = assess_request(
        request, ReviewPolicy(), known_team=True, as_of=request.prediction_cutoff
    )
    assert status == "REVIEW_REQUIRED"
    assert {item.code for item in warnings} == {"TIMING_UNVERIFIED", "FRESHNESS_UNVERIFIED"}


@pytest.mark.parametrize(
    "field,value",
    [
        ("input_schema_version", 2),
        ("input_schema_version", True),
        ("scheduled_date", "2030-02-30"),
        ("scheduled_date", "20300102"),
        ("department", "sweing"),
        ("department", "sewing "),
        ("department", None),
        ("team", 1),
        ("team", "01"),
        ("team", "1.0"),
        ("team", "-1"),
        ("prediction_cutoff", "2030-01-02T07:00:00"),
        ("prediction_cutoff", "2030-01-02T07:00:00+25:00"),
        ("prediction_cutoff", "2030-01-03T07:00:00Z"),
        ("source_snapshot_timestamp", "2030-01-02T08:00:00+03:00"),
        ("source_id", ""),
        ("source_id", " x"),
        ("source_id", "x\ny"),
        ("shift_id", ""),
        ("actual_productivity", 0.8),
        ("incentive", 5),
        ("no_of_workers", 20),
    ],
)
def test_invalid_contract_rejected_without_repair(request_payload, field, value):
    with pytest.raises(ContractError):
        PredictionRequest.from_dict({**request_payload, field: value})


@pytest.mark.parametrize("field", ["source_id", "team", "source_snapshot_timestamp"])
def test_missing_fields(request_payload, field):
    del request_payload[field]
    with pytest.raises(ContractError, match="missing"):
        PredictionRequest.from_dict(request_payload)


@pytest.mark.parametrize("text", ['{"x":1,"x":2}', '{"x": NaN}', "[]", "{"])
def test_strict_json(text):
    with pytest.raises(ContractError):
        read_json(text)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"maximum_snapshot_age_seconds": 60},
        {"maximum_snapshot_age_seconds": 0, "freshness_evidence_reference": "test"},
        {"timing_evidence_reference": "test"},
        {"freshness_evidence_reference": "test", "source_id": "test"},
        {"unknown_team_action": "ignore"},
        {"policy_schema_version": True},
    ],
)
def test_policy_requires_evidence_and_binding(kwargs):
    with pytest.raises(ContractError):
        ReviewPolicy(**kwargs)


def test_policy_statuses_and_unknown_team(request_payload):
    request = PredictionRequest.from_dict(request_payload)
    policy = ReviewPolicy(
        source_id=request.source_id,
        timing_evidence_reference="test-only:timing",
        maximum_snapshot_age_seconds=3600,
        freshness_evidence_reference="test-only:freshness",
    )
    assert assess_request(request, policy, known_team=True, as_of=request.prediction_cutoff) == (
        "VALID_EXPERIMENTAL",
        (),
    )
    assert (
        assess_request(request, policy, known_team=False, as_of=request.prediction_cutoff)[0]
        == "REVIEW_REQUIRED"
    )
    strict = ReviewPolicy(source_id=request.source_id, unknown_team_action="abstain")
    assert (
        assess_request(request, strict, known_team=False, as_of=request.prediction_cutoff)[0]
        == "ABSTAIN"
    )


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("stale", "STALE_SNAPSHOT"),
        ("source", "SOURCE_MISMATCH"),
        ("future", "FUTURE_SNAPSHOT"),
        ("late", "CUTOFF_PASSED"),
    ],
)
def test_abstention_policy(request_payload, mode, expected):
    request = PredictionRequest.from_dict(request_payload)
    policy = ReviewPolicy(
        source_id="other" if mode == "source" else request.source_id,
        maximum_snapshot_age_seconds=1 if mode == "stale" else None,
        freshness_evidence_reference="test-only" if mode == "stale" else None,
    )
    as_of = datetime.fromisoformat(
        {
            "future": "2030-01-02T06:00:00+03:00",
            "late": "2030-01-02T08:00:00+03:00",
        }.get(mode, request_payload["prediction_cutoff"])
    )
    status, warnings = assess_request(request, policy, known_team=True, as_of=as_of)
    assert status == "ABSTAIN"
    assert expected in {item.code for item in warnings}
