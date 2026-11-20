import copy
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

import pytest

import loometric.synthetic_export as exporter
from loometric.benchmarks.design import load_design
from loometric.benchmarks.generation import generate_instance
from loometric.planning.loading import parse_json
from loometric.planning.reporting import json_value
from loometric.scheduling.contracts import instance_fingerprint

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def exported():
    before = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in subprocess.check_output(
            ["git", "ls-files", *exporter.FIXTURE_ROOTS, exporter.DESIGN_PATH], cwd=ROOT, text=True
        ).splitlines()
    }
    summary = exporter.export_csv(ROOT)
    with (ROOT / exporter.OUTPUT_PATH).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        assert tuple(reader.fieldnames) == exporter.COLUMNS
        rows = list(reader)
    assert all(
        hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
        for name, digest in before.items()
    )
    return summary, rows


def test_frozen_sources_row_counts_and_unique_record_identity(exported):
    summary, rows = exported
    assert summary["rows"] == len(rows) == 20645
    assert summary["columns"] == 80
    assert summary["source_counts"] == {
        "planning_fixture": 2,
        "scheduling_fixture": 9,
        "schedule_proposal": 2,
        "what_if_specification": 14,
        "what_if_applied": 12,
        "benchmark_generated": 36,
    }
    assert len({row["record_id"] for row in rows}) == len(rows)
    assert all(len(row) == 80 and None not in row and None not in row.values() for row in rows)
    assert Counter(row["record_type"] for row in rows)["order"] == 2250
    assert Counter(row["record_type"] for row in rows)["order_stage"] == 9246
    assert Counter(row["record_type"] for row in rows)["assignment"] == 2944
    assert Counter(row["record_type"] for row in rows)["downtime"] == 2924


def test_complete_declared_generation_grid_including_all_stress_cases(exported):
    _, rows = exported
    design = load_design(ROOT / exporter.DESIGN_PATH)
    generated = [r for r in rows if r["source_kind"] == "benchmark_generated"]
    sources = {r["benchmark_case"]: r for r in generated if r["record_type"] == "source"}
    assert set(sources) == {case.name for case in design.cases}
    assert len(sources) == 36  # Three budgets and two repetitions do not create more inputs.
    for case in design.cases:
        source = sources[case.name]
        assert source["seed"] == str(case.generation.seed)
        assert source["target_load_percent"] == str(case.generation.target_load_percent)
        assert source["instance_fingerprint"] == instance_fingerprint(
            generate_instance(case.generation)
        )
        assert json.loads(source["generation_config_json"]) == json_value(asdict(case.generation))
        execution = json.loads(source["benchmark_execution_config_json"])
        assert execution["wall_budgets_seconds"] == [1, 5, 10] and execution["repetitions"] == 2
    orders = [r for r in generated if r["record_type"] == "order"]
    stages = [r for r in generated if r["record_type"] == "order_stage"]
    assert len(orders) == sum(case.generation.orders for case in design.cases) == 2178
    assert (
        len(stages)
        == sum(case.generation.orders * case.generation.stages for case in design.cases)
        == 9162
    )
    assert sum(r["benchmark_tier"] == "stress" for r in stages) == 9 * 750


def test_explicit_provenance_and_fingerprint_aliases_are_not_independent_data(exported):
    _, rows = exported
    sources = [row for row in rows if row["record_type"] == "source"]
    files = {row["source_path"] for row in sources if row["value_origin"] == "source_input"}
    expected = set(
        subprocess.check_output(
            ["git", "ls-files", *exporter.FIXTURE_ROOTS], cwd=ROOT, text=True
        ).splitlines()
    )
    assert files == expected and len(files) == 27
    for row in sources:
        assert (
            row["source_sha256"]
            == hashlib.sha256((ROOT / row["source_path"]).read_bytes()).hexdigest()
        )
    representative = next(r for r in sources if r["source_path"].endswith("representative.json"))
    generated = next(r for r in sources if r["benchmark_case"] == "small-p90-s42")
    assert representative["instance_fingerprint"] == generated["instance_fingerprint"]
    assert representative["source_id"] != generated["source_id"]
    assert {r["value_origin"] for r in rows} == {
        "source_input",
        "generated_input",
        "transformed_input",
    }
    assert all(r["synthetic"] == "true" for r in rows)


def test_relationship_integrity_and_no_joined_quantity_or_staffing_duplication(exported):
    _, rows = exported
    keys = {row["record_id"] for row in rows}
    sources = {row["source_id"] for row in rows if row["record_type"] == "source"}
    entities = {
        (row["source_id"], row["record_type"], row[field])
        for row in rows
        for field in ("order_id", "style_id", "line_id", "shift_id", "profile_id", "assignment_id")
        if row[field]
    }
    for row in rows:
        if row["parent_record_id"]:
            assert row["parent_record_id"] in keys
        for field in ("context_source_id", "baseline_source_id", "specification_source_id"):
            assert row[field] == "" or row[field] in sources
        if row["record_type"] != "order":
            assert row["quantity"] == ""
        if row["record_type"] != "line":
            assert row["worker_count"] == ""
        references = {
            "order": (("style", "style_id"),),
            "order_stage": (("order", "order_id"), ("style", "style_id")),
            "assignment": (
                ("line", "line_id"),
                ("shift", "shift_id"),
                ("capacity_profile", "profile_id"),
            ),
            "downtime": (("assignment", "assignment_id"),),
            "capability": (("line", "line_id"), ("style", "style_id")),
            "capacity_profile": (("line", "line_id"),),
            "style_standard": (("style", "style_id"),),
            "break": (("shift", "shift_id"),),
            "unavailability": (("line", "line_id"),),
        }
        for target_kind, field in references.get(row["record_type"], ()):
            assert (row["source_id"], target_kind, row[field]) in entities
        if row["record_type"] == "order_stage":
            for line_id in json.loads(row["compatible_line_ids_json"]):
                assert (row["source_id"], "line", line_id) in entities


def test_invalid_inputs_and_proposals_are_visible_without_fabricated_metrics(exported):
    _, rows = exported
    failures = {
        r["source_path"]: r
        for r in rows
        if r["record_type"] == "source" and r["validation_status"] != "VALID_INPUT"
    }
    assert len(failures) == 5
    assert json.loads(
        failures["examples/scenarios/conflicting-changes.json"]["validation_codes_json"]
    ) == ["SCENARIO_CONFLICT"]
    assert json.loads(
        failures["examples/scenarios/invalid-reference.json"]["validation_codes_json"]
    ) == ["UNKNOWN_REFERENCE"]
    assert failures["examples/scheduling/invalid-overlap.json"]["validation_status"] == "INVALID"
    invalid_order = next(
        r
        for r in rows
        if r["record_type"] == "order" and r["source_path"].endswith("invalid-quantity.json")
    )
    assert (
        invalid_order["quantity"] == "0" and invalid_order["validation_status"] == "INVALID_INPUT"
    )
    proposed = [r for r in rows if r["record_type"] == "proposed_allocation"]
    assert len(proposed) == 6 and all(
        r["proposed_quantity"] and r["quantity"] == "" for r in proposed
    )
    assert not {"scheduled_units", "makespan_minutes", "line_utilization", "runtime"} & set(
        exporter.COLUMNS
    )


def test_pure_what_if_projection_preserves_baseline_and_uses_explicit_source_keys(exported):
    _, rows = exported
    original = next(
        r
        for r in rows
        if r["source_id"] == "examples/scenarios/capacity-baseline.json"
        and r["record_type"] == "line"
    )
    changed = next(
        r
        for r in rows
        if r["source_id"] == "examples/scenarios/additional-workers.json#applied"
        and r["record_type"] == "line"
    )
    assert original["worker_count"] == "2" and changed["worker_count"] == "3"
    assert changed["baseline_source_id"] == original["source_id"]
    assert changed["specification_source_id"] == "examples/scenarios/additional-workers.json"
    assert changed["value_origin"] == "transformed_input"
    source_ids = {r["source_id"] for r in rows}
    assert "examples/scenarios/conflicting-changes.json#applied" not in source_ids
    assert "examples/scenarios/invalid-reference.json#applied" not in source_ids
    # Explicit optimizer-requested input is inspectable without starting its solver.
    assert "examples/scenarios/capacity-optimizer-recovery.json#applied" in source_ids


def test_output_bytes_are_reproducible_and_csv_remains_ignored(exported):
    first, _ = exported
    second = exporter.export_csv(ROOT)
    assert first == second
    assert (ROOT / exporter.OUTPUT_PATH).read_bytes().startswith(b"view_schema_version,")
    subprocess.run(["git", "check-ignore", "-q", exporter.OUTPUT_PATH], cwd=ROOT, check=True)
    assert subprocess.check_output(["git", "ls-files", exporter.OUTPUT_PATH], cwd=ROOT) == b""


def test_exact_decimal_projection_and_source_immutability():
    data = parse_json((ROOT / "examples/planning/capacity-demo.json").read_text(encoding="utf-8"))
    exact = "0.1234567890123456789012345678"
    data["capacity_profiles"][0]["assumed_efficiency"] = Decimal(exact)
    before = copy.deepcopy(data)
    source = exporter.Source("test", "test.json", "0" * 64, "planning_fixture", data)
    rows = list(exporter.source_rows(source))
    profile = next(r for r in rows if r["record_type"] == "capacity_profile")
    assert profile["assumed_efficiency"] == exact
    assert json.loads(profile["attributes_json"])["assumed_efficiency"] == exact
    assert data == before


def test_csv_quoting_and_empty_values_round_trip(tmp_path, monkeypatch):
    data = parse_json((ROOT / "examples/planning/capacity-demo.json").read_text(encoding="utf-8"))
    data["label"] = 'Türkçe, "quoted"\ninspection label'
    source = exporter.Source(
        "test",
        "test.json",
        "0" * 64,
        "planning_fixture",
        data,
        validation_status="INVALID_INPUT",
        validation_codes=("INVALID_FIELDS",),
    )
    monkeypatch.setattr(exporter, "collect_sources", lambda root: iter([source]))
    monkeypatch.setattr(exporter, "_git", lambda root, *args: str(tmp_path))
    result = exporter.export_csv(tmp_path)
    with Path(result["output"]).open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["label"] == data["label"]
    assert rows[0]["quantity"] == ""
    assert rows[0]["required_stages_json"] == ""
    assert next(r for r in rows if r["record_type"] == "order")["required_stages_json"].startswith(
        "["
    )


def test_failed_projection_preserves_previous_csv_and_removes_temporary_file(tmp_path, monkeypatch):
    output = tmp_path / exporter.OUTPUT_PATH
    output.parent.mkdir(parents=True)
    output.write_text("previous export", encoding="utf-8")
    monkeypatch.setattr(exporter, "_git", lambda root, *args: str(tmp_path))

    def broken(root):
        raise ValueError("injected projection failure")
        yield  # Keep the failure lazy, after the temporary CSV was opened.

    monkeypatch.setattr(exporter, "collect_sources", broken)
    with pytest.raises(ValueError, match="injected"):
        exporter.export_csv(tmp_path)
    assert output.read_text(encoding="utf-8") == "previous export"
    assert not list(output.parent.glob(".synthetic-data-view-*.tmp"))


def test_standalone_cli_never_imports_or_runs_solver_dispatch_or_ml():
    code = r"""
import importlib.abc,pathlib,sys
sys.path.insert(0,str(pathlib.Path('src').resolve()))
root=pathlib.Path.cwd().resolve()
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        packages=('ortools','pandas','numpy','sklearn','joblib','fastapi','loometric.api',
            'loometric.prediction','loometric.data','loometric.optimization.solver',
            'loometric.optimization.model','loometric.scheduling.dispatcher','loometric.scheduling.metrics')
        if any(fullname==p or fullname.startswith(p+'.') for p in packages):
            raise AssertionError('Forbidden export dependency: '+fullname)
sys.meta_path.insert(0,Block())
def guard(event,args):
    if event=='open' and isinstance(args[0],str):
        path=pathlib.Path(args[0]).resolve()
        if path.is_relative_to(root/'data') and path!=root/'data/processed':
            assert path.parent==root/'data/processed'
            expected=path.name=='synthetic-data-view.csv'
            assert expected or path.name.startswith('.synthetic-data-view-')
sys.addaudithook(guard)
from loometric.synthetic_export import main
assert main([])==0
"""
    result = subprocess.run(
        [sys.executable, "-S", "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert json.loads(result.stdout)["rows"] == 20645
