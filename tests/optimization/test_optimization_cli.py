"""Optimizer CLI, hierarchy-aware comparison and frozen reference regression evidence."""

import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

import loometric.optimization.solver as engine
from loometric.optimization.comparison import compare_quality
from loometric.scheduling.cli import main
from loometric.scheduling.dispatcher import dispatch
from loometric.scheduling.loading import load_instance
from loometric.scheduling.metrics import calculate_metrics

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples/scheduling"
REFERENCE_HASHES = {
    "competition": "b8204cb6a3767171001dfcfa70d39a4e0a9401610a07d4b4c405a2e855dd0550",
    "parallel-routing": "5811b965b347814c4d654e60d723f9b5ab09370b371f72e4738460581cdc0001",
    "calendar-fragments": "9aca328de59b400d95f521e73048452e0a67d54edbb2a287e72d39b8df6458eb",
    "limits": "fd97b17748ad126c700abe9bc787dbe1c15e7901837227643080e23d949f69ff",
    "zero-capacity": "d6718ddf7d771afd29ab68867b238302061d5dbea4a127ce927f3b671aa9a94d",
}


def test_hierarchy_reports_primary_gain_and_secondary_regression_honestly():
    instance = load_instance(EXAMPLES / "hand-enumerated.json")
    reference = calculate_metrics(instance, dispatch(instance))
    optimized = engine.optimize(instance)
    result = compare_quality(optimized.metrics, reference)
    assert result.relation == "BETTER" and result.deciding_objective == "unfinished_units"
    assert result.objective_deltas == {
        "unfinished_units": -4,
        "priority_weighted_tardiness_minutes": 2,
        "makespan_minutes": 4,
    }
    reverse = compare_quality(reference, optimized.metrics)
    assert reverse.relation == "WORSE"  # Lower tardiness cannot rescue fewer finished goods.
    assert compare_quality(reference, reference).relation == "TIE"
    assert compare_quality(None, reference).relation == "NOT_COMPARABLE"


def test_cli_has_explicit_configuration_proof_and_runtime_sections(capsys):
    assert (
        main(
            [
                "optimize",
                "--instance",
                str(EXAMPLES / "competition.json"),
                "--seed",
                "42",
                "--workers",
                "1",
                "--time-limit-seconds",
                "10",
                "--deterministic-time-limit",
                "1",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["algorithm"] == "ortools-cp-sat-lexicographic-v1"
    assert result["ortools_version"] == "9.15.6755" and result["full_lexicographic_optimal"]
    assert result["solver_configuration"]["workers"] == 1
    assert all(p["proven_optimal"] for p in result["phases"])
    assert (
        result["verification"]["feasible"]
        and result["baseline_comparison"]["reference_verification"]["feasible"]
    )
    assert result["baseline_comparison"]["comparison"]["relation"] == "BETTER"
    assert result["runtime"]["optimizer"]["total_seconds"] >= 0


def test_cli_reproducibility_separates_only_runtime(capsys):
    arguments = ["optimize", "--instance", str(EXAMPLES / "parallel-routing.json")]
    assert main(arguments) == 0
    first = json.loads(capsys.readouterr().out)
    assert main(arguments) == 0
    second = json.loads(capsys.readouterr().out)
    first.pop("runtime")
    second.pop("runtime")
    assert first == second


def test_cli_zero_limit_exposes_unknown_without_fabrication(capsys):
    assert (
        main(
            [
                "optimize",
                "--instance",
                str(EXAMPLES / "competition.json"),
                "--time-limit-seconds",
                "0",
            ]
        )
        == 2
    )
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "UNKNOWN" and result["schedule"] is result["metrics"] is None
    assert result["baseline_comparison"]["comparison"]["relation"] == "NOT_COMPARABLE"


def test_cli_invalid_optimizer_candidate_has_no_metrics(monkeypatch, capsys):
    original = engine.adapt_solution

    def corrupt(*args):
        schedule = original(*args)
        return replace(
            schedule,
            allocations=(replace(schedule.allocations[0], consumed_worker_minutes=Decimal(1)),),
        )

    monkeypatch.setattr(engine, "adapt_solution", corrupt)
    assert main(["optimize", "--instance", str(EXAMPLES / "competition.json")]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "INVALID" and result["metrics"] is None
    assert not result["verification"]["feasible"] and not result["full_lexicographic_optimal"]


@pytest.mark.parametrize(
    "argument,value", [("--workers", "2"), ("--time-limit-seconds", "-1"), ("--seed", "-1")]
)
def test_cli_invalid_configuration_is_explicit(argument, value, capsys):
    assert (
        main(["optimize", "--instance", str(EXAMPLES / "competition.json"), argument, value]) == 2
    )
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "INVALID_INPUT" and result["metrics"] is None


@pytest.mark.parametrize("name", tuple(REFERENCE_HASHES))
def test_existing_dispatch_command_remains_byte_identical(name):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "loometric.scheduling",
            "dispatch",
            "--instance",
            str(EXAMPLES / f"{name}.json"),
        ],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    # Historical snapshots use Windows CRLF; normalize only newline encoding elsewhere.
    windows = result.stdout.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    assert hashlib.sha256(windows).hexdigest() == REFERENCE_HASHES[name]


def test_optimizer_reads_no_repository_data_or_m01_artifact():
    source = r"""
import pathlib,sys,json
repo=pathlib.Path.cwd().as_posix().lower()
sys.path.insert(0,str(pathlib.Path('src').resolve()))
def guard(event,args):
    if event=='open' and isinstance(args[0],str):
        path=args[0].replace(chr(92),'/').lower()
        assert not path.startswith(repo+'/data/'),path
        assert not path.startswith(repo+'/src/loometric/prediction/'),path
sys.addaudithook(guard)
from loometric.optimization.solver import optimize
from loometric.scheduling.loading import load_instance
forbidden=('sklearn','joblib','loometric.prediction','loometric.data','loometric.scheduling.dispatcher')
assert not any(name.startswith(forbidden) for name in sys.modules)
result=optimize(load_instance(pathlib.Path('examples/scheduling/competition.json')))
assert result.verification.feasible
print(json.dumps({'status':result.status}))
"""
    result = subprocess.run(
        [sys.executable, "-c", source], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "VALID_PARTIAL"


def test_missing_optional_solver_produces_install_guidance_instead_of_implicit_install():
    source = r"""
import pathlib,sys
sys.path.insert(0,str(pathlib.Path('src').resolve()))
from loometric.scheduling.cli import main
raise SystemExit(main(['optimize','--instance','examples/scheduling/competition.json']))
"""
    result = subprocess.run(
        [sys.executable, "-S", "-c", source], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode == 2
    assert json.loads(result.stdout)["error"]["code"] == "OPTIMIZATION_DEPENDENCY_MISSING"
