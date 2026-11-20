"""Strict wire contracts, reproducible synthetic benchmarks and no ML/data access."""

import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from loometric.planning.reporting import json_value
from loometric.planning.validation import PlanningError
from loometric.scheduling.cli import main
from loometric.scheduling.dispatcher import dispatch
from loometric.scheduling.loading import load_instance, parse_instance, parse_schedule
from loometric.scheduling.verification import verify_schedule

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples/scheduling"
BENCHMARKS = ("competition", "parallel-routing", "calendar-fragments", "limits", "zero-capacity")


@pytest.mark.parametrize("name", BENCHMARKS)
def test_benchmark_results_are_reproducible_and_verified(name, capsys):
    args = ["dispatch", "--instance", str(EXAMPLES / f"{name}.json")]
    assert main(args) == 0
    first = capsys.readouterr().out
    assert main(args) == 0 and capsys.readouterr().out == first
    result = json.loads(first)
    assert result["verification"]["feasible"] and result["metrics"] is not None
    assert result["synthetic"] and not result["optimality_claim"]
    assert result["metrics"]["scheduled_orders"] + result["metrics"]["unscheduled_orders"] == len(
        result["metrics"]["orders"]
    )
    instance = load_instance(EXAMPLES / f"{name}.json")
    proposed = parse_schedule(json.dumps(result["schedule"]))
    assert verify_schedule(instance, proposed).feasible


@pytest.mark.parametrize(
    "name,instance,code",
    [
        ("invalid-overlap", "competition", "RESOURCE_OVERLAP"),
        ("invalid-precedence", "parallel-routing", "PRECEDENCE_VIOLATION"),
    ],
)
def test_intentionally_corrupted_proposals_have_no_metrics(name, instance, code, capsys):
    assert (
        main(
            [
                "verify",
                "--instance",
                str(EXAMPLES / f"{instance}.json"),
                "--schedule",
                str(EXAMPLES / f"{name}.json"),
            ]
        )
        == 2
    )
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "INVALID" and output["metrics"] is None
    assert {item["code"] for item in output["verification"]["violations"]} == {code}


def test_public_proposal_roundtrip_and_verify_command(tmp_path, capsys):
    instance_path = EXAMPLES / "competition.json"
    instance = load_instance(instance_path)
    schedule = dispatch(instance)
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(json.dumps(json_value(asdict(schedule))), encoding="utf-8")
    assert parse_schedule(proposal_path.read_text()) == schedule
    assert main(["verify", "--instance", str(instance_path), "--schedule", str(proposal_path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "VALID_PARTIAL" and result["algorithm"] == "EXTERNAL_PROPOSAL"


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", 2),
        ("policy_version", "split"),
        ("allocation_granularity_minutes", 5),
        ("calendar_utc_offset_minutes", True),
        ("ml_capacity_multiplier", 0.8),
        ("horizon", {"start": "2030-01-07T08:00:00", "end": "2030-01-07T16:00:00"}),
    ],
)
def test_invalid_instance_schema_rejected(field, value):
    raw = json.loads((EXAMPLES / "competition.json").read_text())
    raw[field] = value
    with pytest.raises(PlanningError):
        parse_instance(json.dumps(raw))


@pytest.mark.parametrize("field", ["schema_version", "policy_version", "planning", "horizon"])
def test_required_instance_fields_not_defaulted(field):
    raw = json.loads((EXAMPLES / "competition.json").read_text())
    del raw[field]
    with pytest.raises(PlanningError):
        parse_instance(json.dumps(raw))


@pytest.mark.parametrize(
    "field,value",
    [
        ("consumed_worker_minutes", 225),
        ("consumed_standard_minutes", "NaN"),
        ("required_standard_minutes", " 720"),
        ("required_standard_minutes", "7.2e2"),
        ("quantity", True),
        ("stage", "unknown"),
        ("elapsed_hours", 3.75),
    ],
)
def test_invalid_proposal_fields_rejected(scheduling_instance, field, value):
    raw = json_value(asdict(dispatch(scheduling_instance)))
    raw["allocations"][0][field] = value
    with pytest.raises(PlanningError):
        parse_schedule(json.dumps(raw))


@pytest.mark.parametrize("source", ['{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', "[]", "{"])
def test_strict_json_is_reused(source):
    with pytest.raises(PlanningError):
        parse_instance(source)


def test_invalid_input_and_missing_files_are_structured(tmp_path, capsys):
    assert main(["dispatch", "--instance", str(tmp_path / "missing.json")]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "INVALID_INPUT" and result["metrics"] is None
    path = tmp_path / "bad.json"
    path.write_bytes(b"\xff")
    assert main(["dispatch", "--instance", str(path)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "INVALID_INPUT"


def test_nonsynthetic_cli_is_explicitly_unsupported(tmp_path, capsys):
    raw = json.loads((EXAMPLES / "competition.json").read_text())
    raw["planning"]["synthetic"] = False
    path = tmp_path / "real.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    assert main(["dispatch", "--instance", str(path)]) == 2
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "INSTANCE_NOT_SYNTHETIC"


def test_cli_reads_only_explicit_instance(monkeypatch, capsys):
    path = EXAMPLES / "competition.json"
    original = Path.read_text
    reads = []

    def guarded(actual, *args, **kwargs):
        assert actual == path, f"Unexpected protected-data/artifact access: {actual}"
        reads.append(actual)
        return original(actual, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded)
    assert main(["dispatch", "--instance", str(path)]) == 0
    assert reads == [path] and json.loads(capsys.readouterr().out)["synthetic"]


def test_no_site_packages_solver_ml_or_protected_data():
    source = r"""
import pathlib,sys
sys.path.insert(0,str(pathlib.Path('src').resolve()))
def guard(event,args):
    if event=='open' and isinstance(args[0],str):
        path='/'+args[0].replace(chr(92),'/').lower()
        assert '/data/' not in path and '/prediction/' not in path,path
sys.addaudithook(guard)
from loometric.scheduling.cli import main
forbidden=('pandas','sklearn','joblib','ortools','loometric.prediction','loometric.data')
assert not any(name.startswith(forbidden) for name in sys.modules)
raise SystemExit(main(['dispatch','--instance','examples/scheduling/competition.json']))
"""
    result = subprocess.run(
        [sys.executable, "-S", "-c", source], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "VALID_PARTIAL"
