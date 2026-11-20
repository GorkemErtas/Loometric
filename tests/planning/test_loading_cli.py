"""Strict synthetic JSON, deterministic CLI and isolation from ML/protected data."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from loometric.planning.capacity import assess_scenario
from loometric.planning.cli import main
from loometric.planning.loading import parse_scenario
from loometric.planning.reporting import report_to_dict
from loometric.planning.validation import PlanningError

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/planning/capacity-demo.json"


@pytest.fixture
def planning_payload():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_complete_scenario_contract_and_independent_report(planning_payload):
    scenario = parse_scenario(json.dumps(planning_payload))
    report = assess_scenario(scenario)
    assert len(report.slots) == 6 and len(report.orders) == 6
    assert len(report.assessments) == 42
    assert report.synthetic and report.schedule_feasibility == "NOT_ASSESSED"
    assert {slot.profile_source_id for slot in report.slots} == {"synthetic:m02-demo"}
    assert next(
        o for o in report.orders if o.order_id == "O-MULTI"
    ).all_stages_have_independent_slot
    qc = next(o for o in report.orders if o.order_id == "O-QC")
    assert qc.stage_checks[0].reason_codes == ("NO_COMPATIBLE_SLOT",)


@pytest.mark.parametrize(
    "path,value,code",
    [
        (("schema_version",), 2, "SCHEMA_MISMATCH"),
        (("schema_version",), True, "INVALID_INTEGER"),
        (("synthetic",), "true", "INVALID_SYNTHETIC_FLAG"),
        (("orders", 0, "quantity"), 0, "INVALID_INTEGER"),
        (("orders", 0, "quantity"), 1.5, "INVALID_INTEGER"),
        (("orders", 0, "quantity"), True, "INVALID_INTEGER"),
        (("orders", 0, "release_date"), "01/07/2030", "INVALID_DATE"),
        (("orders", 0, "due_date"), "2030-02-30", "INVALID_DATE"),
        (("orders", 0, "style_id"), "missing", "UNKNOWN_REFERENCE"),
        (("orders", 0, "required_stages"), ["unknown"], "INVALID_ENUM"),
        (("lines", 0, "availability"), "maintenance", "INVALID_ENUM"),
        (("lines", 0, "worker_count"), -1, "INVALID_INTEGER"),
        (("capacity_profiles", 0, "assumed_efficiency"), "0.8", "INVALID_DECIMAL"),
        (("capacity_profiles", 0, "assumed_efficiency"), True, "INVALID_DECIMAL"),
        (("capacity_profiles", 0, "assumed_efficiency"), 1.01, "INVALID_EFFICIENCY"),
        (("capacity_profiles", 0, "source_id"), "", "INVALID_IDENTIFIER"),
        (
            ("styles", 0, "standards", 0, "measurement_unit"),
            "elapsed_minutes_per_piece",
            "UNSUPPORTED_UNIT",
        ),
        (("styles", 0, "output_unit"), "kg", "UNSUPPORTED_UNIT"),
        (("shifts", 0, "interval", "start"), "2030-01-07T08:00:00", "INVALID_TIMESTAMP"),
        (("shifts", 0, "interval", "start"), "2030-01-07T08:00:00+03:60", "INVALID_TIMESTAMP"),
        (("shifts", 0, "interval", "end"), "2030-01-07T07:00:00+03:00", "INVALID_INTERVAL"),
        (("calendar", "assignments", 0, "shift_id"), "missing", "UNKNOWN_REFERENCE"),
        (("calendar", "working_dates"), ["2030-01-07", "2030-01-07"], "DUPLICATE_DATE"),
        (
            ("calendar", "planned_downtime", 0, "interval", "start"),
            "2030-01-07T07:00:00+03:00",
            "DOWNTIME_OUTSIDE_SHIFT",
        ),
        (("assumptions",), [], "INVALID_COLLECTION"),
        (("orders",), {}, "INVALID_COLLECTION"),
    ],
)
def test_invalid_wire_values_rejected(planning_payload, path, value, code):
    target = planning_payload
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = value
    with pytest.raises(PlanningError) as caught:
        parse_scenario(json.dumps(planning_payload))
    assert caught.value.code == code


@pytest.mark.parametrize("field", ["calendar", "styles", "synthetic", "schema_version"])
def test_required_fields_are_not_defaulted(planning_payload, field):
    del planning_payload[field]
    with pytest.raises(PlanningError) as caught:
        parse_scenario(json.dumps(planning_payload))
    assert caught.value.code == "INVALID_FIELDS"


@pytest.mark.parametrize(
    "field", ["model_artifact", "predicted_productivity", "actual_productivity", "over_time"]
)
def test_speculative_and_ml_inputs_rejected(planning_payload, field):
    planning_payload[field] = "unsupported"
    with pytest.raises(PlanningError) as caught:
        parse_scenario(json.dumps(planning_payload))
    assert caught.value.code == "INVALID_FIELDS"


@pytest.mark.parametrize(
    "source,code",
    [
        ('{"x":1,"x":2}', "DUPLICATE_JSON_KEY"),
        ('{"x":NaN}', "INVALID_JSON"),
        ('{"x":Infinity}', "INVALID_JSON"),
        ("{", "INVALID_JSON"),
        ("[]", "INVALID_OBJECT"),
    ],
)
def test_strict_json(source, code):
    with pytest.raises(PlanningError) as caught:
        parse_scenario(source)
    assert caught.value.code == code


def test_cli_deterministic_and_infeasibility_is_not_input_failure(capsys):
    arguments = ["--scenario", str(EXAMPLE)]
    assert main(arguments) == 0
    first = capsys.readouterr().out
    assert main(arguments) == 0
    assert capsys.readouterr().out == first
    result = json.loads(first)
    large = next(order for order in result["orders"] if order["order_id"] == "O-LARGE")
    assert not large["all_stages_have_independent_slot"]
    assert result["status"] == "CAPACITY_ASSESSED" and result["allocation_performed"] is False


def test_invalid_example_is_structured_rejection(capsys):
    assert main(["--scenario", str(ROOT / "examples/planning/invalid-quantity.json")]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result == {
        "schema_version": 1,
        "status": "INVALID_SCENARIO",
        "error": {"code": "INVALID_INTEGER", "message": "quantity must be an integer >= 1."},
    }


@pytest.mark.parametrize(
    "mode,code",
    [
        ("missing", "SCENARIO_UNREADABLE"),
        ("encoding", "INVALID_VALUE"),
        ("not_synthetic", "SCENARIO_NOT_SYNTHETIC"),
    ],
)
def test_cli_input_failures(planning_payload, tmp_path, capsys, mode, code):
    path = tmp_path / "scenario.json"
    if mode == "encoding":
        path.write_bytes(b"\xff")
    elif mode == "not_synthetic":
        planning_payload["synthetic"] = False
        path.write_text(json.dumps(planning_payload), encoding="utf-8")
    assert main(["--scenario", str(path)]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["error"]["code"] == code


def test_nonroute_collection_order_does_not_change_results(planning_payload):
    expected = report_to_dict(assess_scenario(parse_scenario(json.dumps(planning_payload))))
    altered = copy.deepcopy(planning_payload)
    for field in ("styles", "orders", "lines", "shifts", "capacity_profiles", "capabilities"):
        altered[field].reverse()
    for field in ("assignments", "planned_downtime", "unavailable_periods", "working_dates"):
        altered["calendar"][field].reverse()
    assert report_to_dict(assess_scenario(parse_scenario(json.dumps(altered)))) == expected


def test_cli_reads_only_explicit_synthetic_scenario(monkeypatch, capsys):
    original = Path.read_text
    reads = []

    def guarded(path, *args, **kwargs):
        assert path == EXAMPLE, f"Unexpected data/artifact access: {path}"
        reads.append(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded)
    assert main(["--scenario", str(EXAMPLE)]) == 0
    assert reads == [EXAMPLE]
    assert json.loads(capsys.readouterr().out)["synthetic"] is True


def test_standalone_without_site_packages_or_protected_data():
    # -S excludes pandas/sklearn/joblib and the editable package hook. Only src is added.
    source = r"""
import pathlib,sys
sys.path.insert(0, str(pathlib.Path('src').resolve()))
def guard(event,args):
    if event == 'open' and isinstance(args[0], str):
        normalized='/'+args[0].replace(chr(92),'/').lower()
        assert '/data/' not in normalized and '/prediction/' not in normalized, normalized
sys.addaudithook(guard)
from loometric.planning.cli import main
forbidden=('pandas','sklearn','joblib','loometric.prediction','loometric.data')
assert not any(name.startswith(forbidden) for name in sys.modules)
raise SystemExit(main(['--scenario','examples/planning/capacity-demo.json']))
"""
    result = subprocess.run(
        [sys.executable, "-S", "-c", source], cwd=ROOT, text=True, capture_output=True
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["schedule_feasibility"] == "NOT_ASSESSED"
