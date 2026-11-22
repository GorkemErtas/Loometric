import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from loometric.api.codec import decode_body, input_json
from loometric.api.errors import ApiError
from loometric.api.operations import execute
from loometric.api.settings import Settings, default_limits, settings_from_environment
from loometric.planning.loading import parse_json
from loometric.planning.validation import PlanningError


def test_validate_never_dispatches_or_assesses(monkeypatch, fixture_json):
    def forbidden(*args, **kwargs):
        pytest.fail("Validation must not calculate a schedule or capacity")

    monkeypatch.setattr("loometric.api.operations.dispatch", forbidden)
    monkeypatch.setattr("loometric.api.operations.assess_scenario", forbidden)
    instance = fixture_json("scheduling/competition.json")
    assert execute("validate", input_json({"instance": instance}), default_limits())["status"] == (
        "VALID_INPUT"
    )
    for name in ("max_orders", "max_operations"):
        limits = default_limits().model_copy(update={name: 1})
        with pytest.raises(ApiError, match="synchronous API envelope"):
            execute("validate", input_json({"instance": instance}), limits)


@pytest.mark.parametrize("source", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', "{", "01"])
def test_strict_json_rejects_ambiguous_values(source):
    with pytest.raises(ApiError) as caught:
        decode_body(source, default_limits())
    assert caught.value.status == 400 and caught.value.code == "INVALID_JSON"


@pytest.mark.parametrize(
    "source",
    [
        "[" * 25 + "0" + "]" * 25,
        json.dumps([0] * 257),
        json.dumps("x" * 4097),
        "1e101",
        "0." + "1" * 129,
        "1" * 129,
    ],
)
def test_input_complexity_rejected_before_domain(source):
    with pytest.raises(ApiError) as caught:
        decode_body(source, default_limits())
    assert caught.value.code == "INPUT_LIMIT_EXCEEDED"


def test_string_braces_and_escaped_quotes_do_not_count_as_nesting():
    source = json.dumps({"text": '[\\"{{' * 100})
    assert decode_body(source, default_limits()) == json.loads(source)


def test_decimal_round_trip_and_binary_float_prohibition():
    value = decode_body('{"x":0.1234567890123456789012345678}', default_limits())
    assert value["x"] == Decimal("0.1234567890123456789012345678")
    assert parse_json(input_json(value)) == value
    with pytest.raises(ValueError, match="Binary floats"):
        input_json({"x": 0.1})


def test_configuration_is_closed_and_cannot_raise_resource_caps(api_settings):
    limits = default_limits().model_dump()
    for name, value in limits.items():
        with pytest.raises(ValidationError):
            type(default_limits())(**{**limits, name: value * 10000})
    assert api_settings.token.get_secret_value() not in repr(api_settings)


@pytest.mark.parametrize("origin", ["*", "https://example.com", "http://localhost.evil:5173"])
def test_remote_cors_configuration_rejected(api_settings, origin):
    with pytest.raises(ValueError):
        Settings(token=api_settings.token, cors_origins=(origin,))


def test_invalid_environment_configuration_never_discloses_secret(monkeypatch):
    secret = "unsafe injected configuration /private/path"
    monkeypatch.setenv("LOOMETRIC_API_TOKEN", secret)
    with pytest.raises(ValueError) as caught:
        settings_from_environment()
    assert secret not in str(caught.value)
    monkeypatch.delenv("LOOMETRIC_API_TOKEN")
    with pytest.raises(ValueError):
        settings_from_environment()


@pytest.mark.parametrize("body", [{}, {"scenario": {}, "path": "private"}, {"scenario": []}])
def test_pydantic_envelopes_are_closed(body):
    with pytest.raises(ApiError) as caught:
        execute("capacity", input_json(body), default_limits())
    assert caught.value.code == "INVALID_ENVELOPE"


def test_existing_domain_rejects_unknown_fields_and_preserves_decimal(fixture_json):
    body = {"scenario": fixture_json("planning/capacity-demo.json")}
    body["scenario"]["capacity_profiles"][0]["assumed_efficiency"] = Decimal(
        "0.1234567890123456789012345678"
    )
    result = execute("capacity", input_json(body), default_limits())
    assert "0.1234567890123456789012345678" in json.dumps(result)
    body["scenario"]["unrecognized"] = True
    with pytest.raises(PlanningError, match="unsupported fields"):
        execute("capacity", input_json(body), default_limits())


def test_operation_and_change_caps_do_not_change_domain(fixture_json):
    body = {"instance": fixture_json("scheduling/competition.json")}
    limits = default_limits().model_copy(update={"max_operations": 1})
    with pytest.raises(ApiError, match="synchronous API envelope"):
        execute("dispatch", input_json(body), limits)
    compare = {
        "baseline": fixture_json("scenarios/capacity-baseline.json"),
        "specification": fixture_json("scenarios/additional-workers.json"),
    }
    limits = default_limits().model_copy(update={"max_changes": 1})
    compare["specification"]["changes"] *= 2
    with pytest.raises(ApiError, match="synchronous API envelope"):
        execute("compare", input_json(compare), limits)


def test_cp_sat_is_not_executed_even_if_explicitly_requested(fixture_json):
    body = {
        "baseline": fixture_json("scenarios/routing-baseline.json"),
        "specification": fixture_json("scenarios/capacity-optimizer-recovery.json"),
    }
    with pytest.raises(ApiError) as caught:
        execute("compare", input_json(body), default_limits())
    assert caught.value.code == "UNSUPPORTED_METHOD"
