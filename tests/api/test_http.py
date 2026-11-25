import copy
import json
from decimal import Decimal

import anyio
import httpx
import pytest

from loometric.api.app import create_app
from loometric.api.codec import input_json
from loometric.api.schemas import ErrorResponse, SuccessResponse
from loometric.planning.capacity import assess_scenario
from loometric.planning.loading import scenario_from_dict
from loometric.planning.reporting import report_to_dict
from loometric.scenarios.engine import compare_scenario
from loometric.scenarios.loading import parse_specification
from loometric.scheduling.contracts import instance_fingerprint
from loometric.scheduling.loading import parse_instance


def test_validate_input_returns_exact_identity_without_scheduling(http, fixture_json):
    instance = fixture_json("scheduling/competition.json")
    instance["planning"]["styles"][0]["standards"][0]["standard_minutes_per_unit"] = Decimal(
        "0.1234567890123456789012345678"
    )
    original = copy.deepcopy(instance)
    response = http("POST", "/api/v1/scheduling/validate", body={"instance": instance})
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result == {
        "schema_version": 1,
        "policy_version": "whole-stage-minute-v1",
        "synthetic": True,
        "status": "VALID_INPUT",
        "instance_id": instance["instance_id"],
        "instance_fingerprint": instance_fingerprint(parse_instance(input_json(instance))),
    }
    assert instance == original
    assert response.headers["cache-control"] == "no-store"
    assert "/api/v1/scheduling/validate" in http("GET", "/api/v1/openapi.json").json()["paths"]


@pytest.mark.parametrize(
    ("kind", "code"),
    [
        ("quantity", "INVALID_INTEGER"),
        ("date", "INVALID_DATE"),
        ("duplicate", "DUPLICATE_IDENTIFIER"),
        ("reference", "UNKNOWN_REFERENCE"),
        ("break", "BREAK_OUTSIDE_SHIFT"),
        ("downtime", "DOWNTIME_OUTSIDE_SHIFT"),
        ("profile", "PROFILE_NOT_EFFECTIVE"),
        ("offset", "CALENDAR_OFFSET_MISMATCH"),
        ("fields", "INVALID_FIELDS"),
    ],
)
def test_validate_reuses_authoritative_domain_rules(http, fixture_json, kind, code):
    instance = fixture_json("scheduling/competition.json")
    planning = instance["planning"]
    if kind == "quantity":
        planning["orders"][0]["quantity"] = 0
    elif kind == "date":
        planning["orders"][0]["due_date"] = "2030-02-30"
    elif kind == "duplicate":
        planning["orders"].append(copy.deepcopy(planning["orders"][0]))
    elif kind == "reference":
        planning["orders"][0]["style_id"] = "private:must-not-echo"
    elif kind == "break":
        planning["shifts"][0]["breaks"] = [
            {"start": "2030-01-01T00:00:00+03:00", "end": "2030-01-01T00:01:00+03:00"}
        ]
    elif kind == "downtime":
        planning["calendar"]["planned_downtime"] = [
            {
                "downtime_id": "stop",
                "assignment_id": planning["calendar"]["assignments"][0]["assignment_id"],
                "interval": {
                    "start": "2030-01-01T00:00:00+03:00",
                    "end": "2030-01-01T00:01:00+03:00",
                },
                "reason": "private:must-not-echo",
            }
        ]
    elif kind == "profile":
        planning["capacity_profiles"][0]["effective_date"] = "2099-01-01"
    elif kind == "offset":
        instance["calendar_utc_offset_minutes"] = 0
    else:
        planning["private:must-not-echo"] = True
    response = http("POST", "/api/v1/scheduling/validate", body={"instance": instance})
    result = assert_error(response, 422, "DOMAIN_VALIDATION_FAILED")
    assert result.error.details == [{"domain_code": code}]
    assert "must-not-echo" not in response.text


def test_validate_security_and_transport_limits(http, fixture_json):
    path = "/api/v1/scheduling/validate"
    body = {"instance": fixture_json("scheduling/competition.json")}
    assert_error(http("POST", path, body=body, authorized=False), 401, "AUTHENTICATION_REQUIRED")
    assert http("POST", path, body=body, peer="192.0.2.1").status_code == 403
    assert (
        http("POST", path, body=body, headers={"Origin": "https://evil.example"}).status_code == 403
    )
    assert http("POST", path, body=body, headers={"Host": "evil.example"}).status_code == 403
    assert_error(http("POST", path, body={**body, "token": "private"}), 422, "INVALID_ENVELOPE")
    assert http("POST", path, content=" " * 262145).status_code == 413
    for content in ("[" * 25 + "0" + "]" * 25, json.dumps([0] * 257)):
        assert http("POST", path, content=content).status_code == 422
    body["instance"]["planning"]["synthetic"] = False
    assert_error(http("POST", path, body=body), 422, "SYNTHETIC_REQUIRED")


@pytest.fixture
def http(api_settings):
    app = create_app(api_settings)

    def call(method, path, *, body=None, authorized=True, headers=None, peer="127.0.0.1", **kwargs):
        async def run():
            request_headers = {"Content-Type": "application/json"}
            if authorized:
                request_headers["Authorization"] = "Bearer " + api_settings.token.get_secret_value()
            request_headers.update(headers or {})
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app, client=(peer, 1234)),
                base_url="http://127.0.0.1:8000",
            ) as client:
                return await client.request(
                    method,
                    path,
                    content=input_json(body) if body is not None else kwargs.pop("content", None),
                    headers=request_headers,
                    **kwargs,
                )

        return anyio.run(run)

    return call


def assert_error(response, status, code):
    assert response.status_code == status, response.text
    value = ErrorResponse.model_validate(response.json())
    assert value.error.code == code
    assert value.request_id == response.headers["x-request-id"]
    assert response.headers["cache-control"] == "no-store"
    return value


def test_complete_http_workflow_matches_engines_and_is_reproducible(http, fixture_json):
    assert http("GET", "/api/v1/health", authorized=False).json()["data"]["status"] == "ok"
    capability = http("GET", "/api/v1/capabilities").json()["data"]
    assert capability["scheduling_methods"] == ["greedy"]
    assert "prediction" in capability["deferred"]
    planning = fixture_json("planning/capacity-demo.json")
    response = http("POST", "/api/v1/planning/capacity", body={"scenario": planning})
    assert response.status_code == 200, response.text
    report = SuccessResponse.model_validate(response.json()).data
    assert report == report_to_dict(assess_scenario(scenario_from_dict(planning)))
    instance = fixture_json("scenarios/capacity-baseline.json")
    specification = fixture_json("scenarios/additional-workers.json")
    unchanged = copy.deepcopy((instance, specification))
    dispatched = http("POST", "/api/v1/scheduling/dispatch", body={"instance": instance}).json()[
        "data"
    ]
    assert dispatched["status"] == "VALID_PARTIAL"
    assert dispatched["synthetic"] and dispatched["producer"] == "greedy"
    assert dispatched["limitations"] and dispatched["provenance"]["synthetic"]
    verified = http(
        "POST",
        "/api/v1/scheduling/verify",
        body={"instance": instance, "schedule": dispatched["schedule"]},
    ).json()["data"]
    assert verified["verification"] == dispatched["verification"]
    assert verified["metrics"] == dispatched["metrics"]
    assert verified["producer"] == "external_proposal"
    body = {"baseline": instance, "specification": specification}
    first = http("POST", "/api/v1/scenarios/compare", body=body)
    second = http("POST", "/api/v1/scenarios/compare", body=body)
    assert first.status_code == second.status_code == 200
    comparison = first.json()["data"]
    assert comparison == second.json()["data"]
    expected = compare_scenario(
        parse_instance(input_json(instance)), parse_specification(input_json(specification))
    )
    assert {**comparison, "resource_policy": expected["resource_policy"]} == expected
    assert comparison["resource_policy"]["process_memory_mib"] == 256
    assert comparison["resource_policy"]["process_wall_seconds"] == 5
    assert comparison["resource_policy"]["max_operations"] == 96
    assert comparison["synthetic"] and comparison["provenance"]["synthetic"]
    assert comparison["baseline"]["evaluation"]["metrics"]["scheduled_units"] == 45
    assert comparison["scenario"]["evaluation"]["metrics"]["scheduled_units"] == 55
    assert comparison["limitations"]
    assert (instance, specification) == unchanged


def test_independent_verifier_returns_invalid_without_metrics(http, fixture_json):
    instance = fixture_json("scheduling/competition.json")
    schedule = http("POST", "/api/v1/scheduling/dispatch", body={"instance": instance}).json()[
        "data"
    ]["schedule"]
    schedule["instance_fingerprint"] = "0" * 64
    response = http(
        "POST", "/api/v1/scheduling/verify", body={"instance": instance, "schedule": schedule}
    )
    assert response.status_code == 200
    report = response.json()["data"]
    assert report["status"] == "INVALID"
    assert not report["verification"]["feasible"] and report["metrics"] is None


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/capabilities"),
        ("POST", "/planning/capacity"),
        ("POST", "/scheduling/dispatch"),
        ("POST", "/scheduling/verify"),
        ("POST", "/scenarios/compare"),
    ],
)
def test_all_protected_routes_require_authentication(http, method, path):
    response = http(method, "/api/v1" + path, authorized=False, content=b"invalid json")
    assert_error(response, 401, "AUTHENTICATION_REQUIRED")
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("value", ["Bearer wrong", "Basic ignored", "Bearer " + "a" * 160, ""])
def test_invalid_credentials_are_safe(http, value):
    response = http("GET", "/api/v1/capabilities", headers={"Authorization": value})
    assert_error(response, 401, "AUTHENTICATION_REQUIRED")
    assert value == "" or value not in response.text


@pytest.mark.parametrize("peer", ["192.0.2.10", "localhost", "::ffff:192.0.2.10"])
def test_remote_peers_rejected_even_with_forwarded_loopback(http, peer):
    assert_error(
        http("GET", "/api/v1/health", peer=peer, headers={"X-Forwarded-For": "127.0.0.1"}),
        403,
        "LOCAL_ACCESS_ONLY",
    )


@pytest.mark.parametrize("host", ["evil.example", "localhost.evil:8000", "127.0.0.1:99999"])
def test_host_rebinding_rejected(http, host):
    assert_error(http("GET", "/api/v1/health", headers={"Host": host}), 403, "LOCAL_HOST_REQUIRED")


def test_cors_is_explicit_and_does_not_enable_credentials(http):
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization, Content-Type",
    }
    response = http("OPTIONS", "/api/v1/scenarios/compare", authorized=False, headers=headers)
    assert response.status_code == 204
    assert response.headers["access-control-allow-origin"] == headers["Origin"]
    assert "access-control-allow-credentials" not in response.headers
    assert_error(
        http("GET", "/api/v1/health", headers={"Origin": "http://evil.example"}),
        403,
        "ORIGIN_REJECTED",
    )
    headers["Access-Control-Request-Headers"] = "X-Unsupported"
    assert_error(http("OPTIONS", "/api/v1/health", headers=headers), 403, "CORS_REJECTED")


@pytest.mark.parametrize(
    "content", [b'{"scenario":{},"scenario":{}}', b'{"x":NaN}', b'{"x":Infinity}', b"{", b"\xff"]
)
def test_malformed_and_ambiguous_json_are_rejected(http, content):
    assert_error(http("POST", "/api/v1/planning/capacity", content=content), 400, "INVALID_JSON")


def test_unknown_envelope_fields_and_unsupported_policy_are_rejected(http, fixture_json):
    assert_error(
        http("POST", "/api/v1/planning/capacity", body={"scenario": {}, "path": "private"}),
        422,
        "INVALID_ENVELOPE",
    )
    instance = fixture_json("scheduling/competition.json")
    instance["policy_version"] = "unsupported"
    response = http("POST", "/api/v1/scheduling/dispatch", body={"instance": instance})
    assert_error(response, 422, "DOMAIN_VALIDATION_FAILED")


def test_request_size_is_rejected_before_worker_execution(http):
    assert_error(
        http("POST", "/api/v1/planning/capacity", content=b" " * 262145), 413, "BODY_TOO_LARGE"
    )
    assert_error(
        http("POST", "/api/v1/planning/capacity", headers={"Content-Length": "262145"}),
        413,
        "BODY_TOO_LARGE",
    )


@pytest.mark.parametrize("content", ["[" * 25 + "0" + "]" * 25, json.dumps([0] * 257), "1e101"])
def test_complexity_error_is_structured(http, content):
    assert_error(
        http("POST", "/api/v1/planning/capacity", content=content.encode()),
        422,
        "INPUT_LIMIT_EXCEEDED",
    )


def test_media_and_http_errors_are_uniform(http):
    assert_error(
        http(
            "POST",
            "/api/v1/planning/capacity",
            content=b"{}",
            headers={"Content-Type": "text/plain"},
        ),
        415,
        "JSON_REQUIRED",
    )
    assert_error(
        http(
            "POST", "/api/v1/planning/capacity", content=b"{}", headers={"Content-Encoding": "gzip"}
        ),
        415,
        "CONTENT_ENCODING_UNSUPPORTED",
    )
    assert_error(http("GET", "/missing"), 404, "HTTP_ERROR")
    assert_error(http("DELETE", "/api/v1/health"), 405, "HTTP_ERROR")
    assert_error(http("GET", "/api/v1/health?path=secret"), 400, "UNSUPPORTED_QUERY")


def test_openapi_documents_authentication_envelopes_and_errors(http):
    spec = http("GET", "/api/v1/openapi.json", authorized=False).json()
    assert len(spec["paths"]) == 13
    for suffix, version, count in (("", 1, 3), ("/v2", 2, 4)):
        operation = spec["paths"][f"/api/v1/predictions/synthetic{suffix}"]["post"]
        schema = operation["requestBody"]["content"]["application/json"]["schema"]
        assert schema["properties"]["schema_version"]["const"] == version
        models = schema["properties"]["models"]
        assert models["maxItems"] == count
        assert ("rf_physics" in models["items"]["enum"]) is (version == 2)
    assert spec["components"]["securitySchemes"]["LocalBearer"]["scheme"] == "bearer"
    for path, methods in spec["paths"].items():
        for method, operation in methods.items():
            if path.endswith("/health"):
                assert not operation.get("security")
            else:
                assert operation["security"] == [{"LocalBearer": []}]
            if method == "post":
                schema = operation["requestBody"]["content"]["application/json"]["schema"]
                assert schema["additionalProperties"] is False
                assert "504" in operation["responses"]
    docs = http("GET", "/api/v1/docs", authorized=False)
    assert docs.status_code == 200 and "openapi.json" in docs.text
    assert "https://" not in docs.text


def test_http_decimal_precision_matches_existing_instance_fingerprint(http, fixture_json):
    instance = fixture_json("scenarios/capacity-baseline.json")
    precision = "0.1234567890123456789012345678"
    instance["planning"]["capacity_profiles"][0]["assumed_efficiency"] = Decimal(precision)
    response = http("POST", "/api/v1/scheduling/dispatch", body={"instance": instance})
    assert response.status_code == 200, response.text
    expected = instance_fingerprint(parse_instance(input_json(instance)))
    assert response.json()["data"]["instance_fingerprint"] == expected
    planning = fixture_json("planning/capacity-demo.json")
    planning["capacity_profiles"][0]["assumed_efficiency"] = Decimal(precision)
    capacity = http("POST", "/api/v1/planning/capacity", body={"scenario": planning})
    assert precision in capacity.text


def test_cp_sat_api_request_rejected_without_solver_execution(http, fixture_json):
    body = {
        "baseline": fixture_json("scenarios/routing-baseline.json"),
        "specification": fixture_json("scenarios/capacity-optimizer-recovery.json"),
    }
    assert_error(http("POST", "/api/v1/scenarios/compare", body=body), 422, "UNSUPPORTED_METHOD")


def test_invalid_unicode_and_malformed_content_type_are_not_normalized(http):
    assert_error(
        http("POST", "/api/v1/planning/capacity", content=b'{"x":"\\ud800"}'), 400, "INVALID_JSON"
    )
    assert_error(
        http(
            "POST",
            "/api/v1/planning/capacity",
            content=b"{}",
            headers={"Content-Type": "app lication/json"},
        ),
        415,
        "JSON_REQUIRED",
    )
