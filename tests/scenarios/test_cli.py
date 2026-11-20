"""Offline wire output, deterministic greedy, optional-dependency and ML isolation."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from loometric.scenarios.cli import main
from loometric.scenarios.loading import parse_specification

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples/scenarios"


def test_greedy_cli_is_byte_reproducible_and_reports_units(capsys):
    args = [
        "--baseline",
        str(EXAMPLES / "capacity-baseline.json"),
        "--scenario",
        str(EXAMPLES / "additional-workers.json"),
    ]
    assert main(args) == 0
    first = capsys.readouterr().out
    assert main(args) == 0
    second = capsys.readouterr().out
    assert first == second
    result = json.loads(first)
    assert result["status"] == "VALID_COMPARISON"
    assert result["runtime"] == {"baseline": None, "scenario": None}
    assert result["metric_deltas"]["available_standard_minutes"]["unit"] == "standard_worker_minute"
    assert (
        result["baseline"]["identity"]["instance_fingerprint"]
        != result["scenario"]["identity"]["instance_fingerprint"]
    )
    assert result["scenario"]["evaluation"]["selected_algorithm"] == "serial-priority-due-id-v1"


@pytest.mark.parametrize(
    "name,code",
    [("invalid-reference", "UNKNOWN_REFERENCE"), ("conflicting-changes", "SCENARIO_CONFLICT")],
)
def test_invalid_scenarios_return_only_error_json(name, code, capsys):
    assert (
        main(
            [
                "--baseline",
                str(EXAMPLES / "capacity-baseline.json"),
                "--scenario",
                str(EXAMPLES / f"{name}.json"),
            ]
        )
        == 2
    )
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "INVALID_INPUT" and result["error"]["code"] == code
    assert result["metrics"] is None and "baseline" not in result


def test_fractional_solver_budgets_are_explicitly_parsed():
    data = json.loads((EXAMPLES / "additional-workers.json").read_text())
    data["scheduling"] = {
        "method": "greedy_with_cp_sat",
        "solver": {"wall_time_seconds_per_phase": 0.25, "deterministic_time_per_phase": 0.1},
    }
    request = parse_specification(json.dumps(data)).scheduling
    assert request.solver.wall_time_seconds_per_phase == 0.25
    assert request.solver.deterministic_time_per_phase == 0.1


@pytest.mark.parametrize("value", ["10.0000000000000000001", "1e-1000"])
def test_fractional_budgets_do_not_silently_round_into_bounds(value):
    source = (EXAMPLES / "capacity-optimizer-recovery.json").read_text()
    source = source.replace(
        '"method": "greedy_with_cp_sat"',
        f'"method": "greedy_with_cp_sat", "solver": {{"wall_time_seconds_per_phase":{value}}}',
    )
    with pytest.raises(ValueError):
        parse_specification(source)


def test_cli_greedy_runs_without_site_packages_and_reads_no_protected_data():
    code = r"""
import pathlib,sys
sys.path.insert(0,str(pathlib.Path('src').resolve()))
repo=pathlib.Path.cwd().as_posix().lower()
def guard(event,args):
    if event=='open' and isinstance(args[0],str):
        path=args[0].replace(chr(92),'/').lower()
        assert not path.startswith(repo+'/data/'),path
        assert not path.startswith(repo+'/src/loometric/prediction/'),path
sys.addaudithook(guard)
from loometric.scenarios.cli import main
assert main(['--baseline','examples/scenarios/capacity-baseline.json',
    '--scenario','examples/scenarios/additional-workers.json'])==0
forbidden=('sklearn','joblib','ortools','loometric.prediction','loometric.data')
assert not any(name.startswith(forbidden) for name in sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-S", "-c", code], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["scenario"]["evaluation"]["metrics"]["scheduled_units"] == 55


def test_native_worker_missing_optional_dependency_is_explicit():
    code = r"""
import pathlib,sys,json
sys.path.insert(0,str(pathlib.Path('src').resolve()))
from dataclasses import asdict
from loometric.execution import ResourceLimits
from loometric.optimization.configuration import SolverConfiguration
from loometric.scenarios.worker import run
payload=run({'instance_json':pathlib.Path('examples/scenarios/routing-baseline.json').read_text(),
    'resource_limits':asdict(ResourceLimits()),'solver_configuration':asdict(SolverConfiguration())})
assert payload['status']=='OPTIMIZATION_DEPENDENCY_MISSING'
assert 'optimization' not in payload
"""
    result = subprocess.run(
        [sys.executable, "-S", "-c", code], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
