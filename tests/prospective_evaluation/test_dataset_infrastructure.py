"""Private 35-day mechanical sources only; never the eight actual EXP-009 datasets."""

import copy
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, replace
from datetime import date

import pytest

from loometric.prospective_evaluation import generation, receipts, service, storage
from loometric.prospective_evaluation.protocol import CasePlan, load_protocol, verify_frozen_sources
from loometric.prospective_evaluation.source import (
    SourceDesign,
    audit_source,
    declared_designs,
    expected_source,
)
from loometric.synthetic_ml.configuration import GenerationConfig
from loometric.synthetic_ml.generation import generate
from loometric.synthetic_ml.splitting import date_partitions


@pytest.fixture(scope="module")
def designs():
    result = []
    for seed in (99101, 99211, 99307, 99401):
        for condition in ("baseline", "disruption"):
            config = GenerationConfig(
                seed=seed,
                scenario=condition,
                start_date=date(2032, 1, 5),
                calendar_days=35,
                factories=2,
                styles=3,
            )
            dates = date_partitions(config)
            score = tuple(d for d, p in dates.items() if p == "validation")
            rows = sum(40 if p == "test" else 10 for p in dates.values())
            case = CasePlan(
                f"private-{seed}-{condition}",
                f"private-world-{seed}",
                seed,
                condition,
                score,
                len(score) * 10,
                rows,
                "unused-internal-test-seam",
            )
            result.append(SourceDesign(case, config))
    return tuple(result)


@pytest.fixture(scope="module")
def history():
    keys = frozenset({("factory", "historical-private-42", "F00")})
    return receipts.HistoricalInventory(
        keys,
        {
            "bindings": {},
            "entities_sha256": storage.sha256(storage.encode(sorted(keys))),
            "reserved_labels_decoded": False,
        },
    )


@pytest.fixture(scope="module")
def prepared(tmp_path_factory, designs, history):
    root = tmp_path_factory.mktemp("private-exp009") / "source-root"
    original = generation.generate
    calls = []

    def mechanical_only(config):
        assert config.seed >= 99000 and config.calendar_days == 35
        calls.append((config.seed, config.scenario))
        return original(config)

    patch = pytest.MonkeyPatch()
    patch.setattr(generation, "generate", mechanical_only)
    try:
        result = generation._prepare_batch(root, designs, history)
    finally:
        patch.undo()
    assert len(calls) == 16 and all(
        calls.count((d.case.seed, d.case.condition)) == 2 for d in designs
    )
    return root, result["datasets"]


@pytest.fixture
def private_bundle(prepared, tmp_path):
    root = tmp_path / "private"
    shutil.copytree(prepared[0], root)
    return root, copy.deepcopy(prepared[1])


def manifest_path(root, design):
    return root / generation.case_relative(design) / "manifest.json"


def reseal(root, design, expected):
    path = manifest_path(root, design)
    manifest = json.loads(path.read_bytes())
    for name in manifest["files"]:
        manifest["files"][name] = storage.identity((path.parent / name).read_bytes())
    manifest["replay"]["files"] = copy.deepcopy(manifest["files"])
    content = storage.encode(manifest)
    path.write_bytes(content)
    expected[design.case.case_id] = storage.sha256(content)


def test_declared_policy_is_exact_and_no_generation_is_implicit(monkeypatch):
    config = load_protocol()
    verify_frozen_sources(config)
    actual = declared_designs()
    assert len(actual) == 8 and {d.configuration.seed for d in actual} == {101, 211, 307, 401}
    assert all(d.case.planned_rows == 360 and d.case.source_rows == 2720 for d in actual)
    monkeypatch.setattr(
        service, "_execute", lambda *a: pytest.fail("Unapproved generation launched")
    )
    for value in (False, 1, "yes", None):
        with pytest.raises(ValueError, match="AUTHORIZATION_REQUIRED"):
            service.prepare_sources(generation_authorized=value)
    assert not storage.output_root().exists()


def test_frozen_adapter_reconstruction_has_exact_actual_source_joins(designs):
    for design in designs[:2]:
        data = generate(design.configuration)  # Private mechanical fixture, not a declared case.
        audit_source(data, design)
        assert all(
            getattr(data, name) == getattr(expected_source(design.configuration), name)
            for name in ("factories", "crews", "standards", "plans", "membership")
        )
    assert generation.projection_files(generate(designs[0].configuration), designs[0]) == (
        generation.projection_files(generate(designs[1].configuration), designs[1])
    )


def test_complete_registration_and_independent_verification_never_generate_or_decode_labels(
    private_bundle, designs, history, monkeypatch
):
    root, expected = private_bundle
    monkeypatch.setattr(
        generation, "generate", lambda *a: pytest.fail("Registrar generated outcomes")
    )
    result = receipts._register_batch(root, designs, expected, history)
    assert result["cases"] == 8 and result["promotion_decision"] == "NO_ML_PROMOTION"
    verified = receipts._verify_ledger(root, designs, result["ledger_sha256"], history)
    assert verified["status"] == "INDEPENDENT_LEDGER_AND_SOURCES_VERIFIED"
    assert result["ledger_sha256"] == storage.sha256((root / "receipts/datasets.json").read_bytes())
    with pytest.raises(ValueError, match="CREATE_ONLY_LEDGER"):
        receipts._register_batch(root, designs, expected, history)
    with pytest.raises(ValueError, match="LEDGER_RECEIPT_DRIFT"):
        receipts._verify_ledger(root, designs, "0" * 64, history)


def test_private_repeated_publication_and_receipt_ledgers_are_byte_identical(
    prepared, designs, history, tmp_path
):
    repeat = tmp_path / "repeat"
    result = generation._prepare_batch(repeat, designs, history)
    assert result["datasets"] == prepared[1]
    assert all(
        path.read_bytes() == (repeat / path.relative_to(prepared[0])).read_bytes()
        for path in prepared[0].rglob("*")
        if path.is_file()
    )


@pytest.mark.parametrize(
    "name",
    [
        "manifest.json",
        "plans.jsonl",
        "features.jsonl",
        "scoped_entities.jsonl",
        "score_ids.jsonl",
        "labels.test.jsonl",
        "labels.validation.jsonl",
        "outcomes.jsonl",
    ],
)
def test_any_tampering_fails_before_registration(private_bundle, designs, history, name):
    root, expected = private_bundle
    path = manifest_path(root, designs[0]).parent / name
    path.write_bytes(path.read_bytes() + b"tampered")
    with pytest.raises(ValueError):
        receipts._register_batch(root, designs, expected, history)
    assert not (root / "receipts/datasets.json").exists()


@pytest.mark.parametrize(
    "name,mutation",
    [
        ("plans.jsonl", lambda r: r.update(crew_id="C-FOREIGN-LINE")),
        ("plans.jsonl", lambda r: r.update(snapshot_at="2033-01-01T00:00:00+00:00")),
        (
            "crews.jsonl",
            lambda r: r.update(skill_level=6 - r["skill_level"] if r["skill_level"] != 3 else 1),
        ),
        ("lines.jsonl", lambda r: r.update(factory_id="F99")),
        ("features.jsonl", lambda r: r["inputs"].update(actual_productivity="FORBIDDEN")),
        ("features.jsonl", lambda r: r["inputs"].update(planned_workers=99)),
        ("scoped_entities.jsonl", lambda r: r.update(world_id="renamed-old-world")),
        ("membership.jsonl", lambda r: r.update(partition="validation")),
    ],
)
def test_rehashed_source_forgery_leakage_or_seed_alias_still_fails(
    private_bundle, designs, history, name, mutation
):
    root, expected = private_bundle
    path = manifest_path(root, designs[0]).parent / name
    rows = [json.loads(line) for line in path.read_bytes().splitlines()]
    mutation(rows[0])
    path.write_bytes(storage.records_bytes(rows))
    reseal(
        root, designs[0], expected
    )  # Simulate a faulty publisher, beyond a simple hash mismatch.
    with pytest.raises(ValueError, match="SOURCE_JOIN_FEATURE_OR_ENTITY"):
        receipts._register_batch(root, designs, expected, history)


@pytest.mark.parametrize(
    "field,value",
    [
        ("seed", 42),
        ("condition", "workload_surge"),
        ("dataset_version", "synthetic-ml-v1"),
        ("promotion_decision", "PROMOTED"),
        ("reserved_labels_decoded_by_registrar", True),
        ("unexpected", True),
    ],
)
def test_closed_manifest_policy_even_with_private_trusted_receipt(
    private_bundle, designs, history, field, value
):
    root, expected = private_bundle
    path = manifest_path(root, designs[0])
    manifest = json.loads(path.read_bytes())
    manifest[field] = value
    path.write_bytes(storage.encode(manifest))
    expected[designs[0].case.case_id] = storage.sha256(path.read_bytes())
    with pytest.raises(ValueError, match="POLICY_OR_PROVENANCE"):
        receipts._register_batch(root, designs, expected, history)


@pytest.mark.parametrize(
    "failure", ["missing_manifest", "missing_file", "extra_file", "extra_directory"]
)
def test_incomplete_or_open_publications_rejected(private_bundle, designs, history, failure):
    root, expected = private_bundle
    folder = manifest_path(root, designs[0]).parent
    if failure == "missing_manifest":
        (folder / "manifest.json").unlink()
    elif failure == "missing_file":
        (folder / "plans.jsonl").unlink()
    elif failure == "extra_file":
        (folder / "extra.txt").write_bytes(b"extra")
    else:
        (folder / "extra").mkdir()
    with pytest.raises(ValueError, match="CLOSED_DATASET_FILE_SET"):
        receipts._register_batch(root, designs, expected, history)


def test_source_replay_failure_is_not_published(designs, monkeypatch):
    design = designs[0]
    data = generate(design.configuration)
    altered = replace(
        data.outcomes[0], difficult_condition=not data.outcomes[0].difficult_condition
    )
    calls = iter((data, replace(data, outcomes=(altered, *data.outcomes[1:]))))
    monkeypatch.setattr(generation, "generate", lambda *a: next(calls))
    with pytest.raises(ValueError, match="DETERMINISTIC_SOURCE_REPLAY_FAILED"):
        generation._publication_buffers(design)


def test_existing_partial_case_aborts_before_generator(
    private_bundle, designs, history, monkeypatch
):
    root, _ = private_bundle
    monkeypatch.setattr(
        generation, "generate", lambda *a: pytest.fail("Existing output regenerated")
    )
    with pytest.raises(ValueError, match="CREATE_ONLY_DATASET"):
        generation._prepare_batch(root, designs, history)


def test_independent_receipts_exact_cases_and_history_aliases(private_bundle, designs, history):
    root, expected = private_bundle
    bad = dict(expected)
    bad.pop(designs[-1].case.case_id)
    with pytest.raises(ValueError, match="EIGHT_INDEPENDENT"):
        receipts._register_batch(root, designs, bad, history)
    for sha in ("", None, "../receipt", "a" * 63):
        with pytest.raises(ValueError, match="INDEPENDENT_RECEIPT"):
            receipts._inspect_dataset(root, designs[0], sha, history)
    collision = receipts.HistoricalInventory(
        frozenset({("factory", designs[0].case.world_id, "F00")}), history.receipt
    )
    with pytest.raises(ValueError, match="HISTORICAL_ENTITY_ALIAS"):
        receipts._inspect_dataset(root, designs[0], expected[designs[0].case.case_id], collision)


def test_pair_mismatch_cannot_hide_beyond_namespace(prepared, designs, history):
    left = receipts._inspect_dataset(
        prepared[0], designs[0], prepared[1][designs[0].case.case_id], history
    )
    right = copy.deepcopy(left)
    right["condition"] = "disruption"
    right["files"]["plans.jsonl"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="INPUT_DRIFT"):
        generation.pair_check(left, right)
    right["seed"] += 1
    with pytest.raises(ValueError, match="MATCHED_CASE_PAIR"):
        generation.pair_check(left, right)


def test_forbidden_files_remain_opaque_and_cannot_use_the_json_decoder(
    private_bundle, designs, history
):
    root, expected = private_bundle
    folder = manifest_path(root, designs[0]).parent
    for name in storage.RESERVED:
        count = storage.identity((folder / name).read_bytes())["rows"]
        (folder / name).write_bytes(b"RESERVED_VALUES_NOT_JSON\n" * count)
        with pytest.raises(ValueError, match="RESERVED_LABEL_DECODE_FORBIDDEN"):
            storage.decode_rows(name, b"{}\n")
    reseal(root, designs[0], expected)
    # This deliberately re-signed *private* fixture proves decoding is impossible,
    # not that a malicious publisher's new receipt proves physical label validity.
    receipts._inspect_dataset(root, designs[0], expected[designs[0].case.case_id], history)


def test_paths_and_byte_limits_fail_closed(private_bundle, designs, history, tmp_path, monkeypatch):
    root, expected = private_bundle
    for name in ("../outside", str(tmp_path.absolute()), "datasets/../../raw"):
        with pytest.raises(ValueError):
            storage.safe_path(root, name)
    monkeypatch.setattr(storage, "MAX_ROOT_BYTES", 1)
    with pytest.raises(ValueError, match="ROOT_BYTE_LIMIT"):
        receipts._inspect_dataset(root, designs[0], expected[designs[0].case.case_id], history)
    monkeypatch.setattr(storage, "MAX_ROOT_BYTES", 768 * 1024**2)
    monkeypatch.setattr(receipts, "MAX_FILE_BYTES", 1)
    with pytest.raises(ValueError, match="BUNDLE_BYTE_LIMIT"):
        receipts._inspect_dataset(root, designs[0], expected[designs[0].case.case_id], history)


def test_publication_interruption_never_writes_completion_marker(designs, tmp_path, monkeypatch):
    root = tmp_path / "interrupted"
    root.mkdir()
    original = storage.write_new
    calls = 0

    def fail(root, name, content):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("private injected disk interruption")
        return original(root, name, content)

    monkeypatch.setattr(generation, "write_new", fail)
    history = receipts.HistoricalInventory(frozenset(), {"private": True})
    with pytest.raises(OSError):
        generation._prepare_batch(root, designs, history)
    assert not manifest_path(root, designs[0]).exists()
    assert not (root / "receipts/datasets.json").exists()
    assert any(root.rglob("*.jsonl"))  # Incomplete evidence retained; never silently deleted.


def test_historical_inventory_reads_only_verified_references(designs, tmp_path):
    source = expected_source(designs[0].configuration)
    directory = tmp_path / "historical"
    directory.mkdir()
    files = {}
    for table in receipts.REFERENCE_TABLES:
        content = storage.records_bytes(getattr(source, table))
        (directory / f"{table}.jsonl").write_bytes(content)
        files[f"{table}.jsonl"] = storage.identity(content)
    for name in storage.RESERVED:
        (directory / name).write_bytes(b"UNREADABLE_RESERVED_HISTORY")
    manifest = {
        "dataset_version": "synthetic-ml-v1",
        "generator_version": "stage-shift-process-v1",
        "configuration": asdict(designs[0].configuration),
        "files": files,
    }
    raw = storage.encode(manifest)
    (directory / "manifest.json").write_bytes(raw)
    binding = {
        "directory": "historical",
        "case_id": "private-historical",
        "expected_manifest_fingerprint": storage.sha256(raw),
        "profile": "private",
        "seed": designs[0].case.seed,
        "scenario": "baseline",
    }
    result = receipts._historical_inventory((binding,), tmp_path)
    assert result.keys and result.receipt["reserved_labels_decoded"] is False
    (directory / "crews.jsonl").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="HISTORICAL_REFERENCE_DRIFT"):
        receipts._historical_inventory((binding,), tmp_path)


def test_runtime_reserved_access_guard_is_narrow_and_ml_free(tmp_path):
    script = r"""
import pathlib,sys
from loometric.prospective_evaluation.storage import (
    install_access_guard,opaque_identity,decode_rows,
)
root=pathlib.Path(sys.argv[1]).resolve()
path=root/'labels.test.jsonl'
path.write_bytes(b'OPAQUE_PRIVATE\n')
install_access_guard(root,())
for read in (lambda:path.read_bytes(),lambda:open(path,'rb')):
    try: read()
    except PermissionError: pass
    else: raise AssertionError('Forbidden label read succeeded')
assert opaque_identity(path)['bytes']>0
try: path.read_bytes()
except PermissionError: pass
else: raise AssertionError('Hash capability leaked')
try: __import__('joblib')
except PermissionError: pass
else: raise AssertionError('ML import succeeded')
assert not any(n.split('.')[0] in {'pandas','numpy','sklearn','joblib'} for n in sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)], capture_output=True, text=True, timeout=20
    )
    assert result.returncode == 0, result.stderr


def test_new_worker_is_bounded_without_generating_any_source():
    from loometric.execution import guarded_child

    payload, measurements = guarded_child(
        "{}", 2048, 0.001, worker_module="loometric.prospective_evaluation.worker"
    )
    assert payload is None and measurements["status"] == "TERMINATED_RESOURCE_LIMIT"


def test_native_worker_rejects_unapproved_generation_under_memory_guard():
    from loometric.execution import guarded_child

    payload, measured = guarded_child(
        json.dumps({"operation": "prepare", "generation_authorized": False}),
        2048,
        10,
        worker_module="loometric.prospective_evaluation.worker",
    )
    assert payload == {"error": {"code": "GENERATION_NOT_AUTHORIZED"}}, measured
    assert measured["returncode"] == 0 and measured["whole_child_wall_seconds"] < 10
    assert not storage.output_root().exists()


def test_offline_dispatch_uses_frozen_limits_and_never_an_api_endpoint(monkeypatch):
    seen = []

    def bounded(request, memory, deadline, **kwargs):
        seen.append((json.loads(request), memory, deadline, kwargs))
        return {"status": "PRIVATE_DISPATCH_ONLY"}, {"whole_child_wall_seconds": 0.01}

    monkeypatch.setattr(service, "guarded_child", bounded)
    assert service.register_sources({})["status"] == "PRIVATE_DISPATCH_ONLY"
    request, memory, deadline, kwargs = seen[0]
    assert request["operation"] == "register" and memory == 2048 and deadline == 1200
    assert kwargs["worker_module"] == "loometric.prospective_evaluation.worker"


@pytest.mark.parametrize(
    "name",
    [
        "outcomes.jsonl",
        "labels.train.jsonl",
        "labels.validation.jsonl",
        "labels.gap.jsonl",
        "labels.test.jsonl",
    ],
)
def test_rehashed_opaque_file_still_needs_exact_row_counts(private_bundle, designs, history, name):
    root, expected = private_bundle
    path = manifest_path(root, designs[0]).parent / name
    path.write_bytes(b"NOT_JSON\n")
    reseal(root, designs[0], expected)
    with pytest.raises(ValueError, match="ROW_COUNT_DRIFT"):
        receipts._register_batch(root, designs, expected, history)


def test_ninth_dataset_is_never_silently_ignored(private_bundle, designs, history):
    root, expected = private_bundle
    (root / "datasets/private-unregistered-ninth-case").mkdir()
    with pytest.raises(ValueError, match="CLOSED_EIGHT_DATASET"):
        receipts._register_batch(root, designs, expected, history)


@pytest.mark.parametrize("name", ["plans.jsonl", "manifest.json"])
def test_changes_during_inspection_fail_before_registration(
    private_bundle, designs, history, monkeypatch, name
):
    root, expected = private_bundle
    original = receipts.decode_rows
    replaced = False

    def race(file_name, content):
        nonlocal replaced
        if not replaced:
            path = manifest_path(root, designs[0]).parent / name
            path.write_bytes(path.read_bytes() + b" ")
            replaced = True
        return original(file_name, content)

    monkeypatch.setattr(receipts, "decode_rows", race)
    with pytest.raises(ValueError):
        receipts._register_batch(root, designs, expected, history)
    assert not (root / "receipts/datasets.json").exists()


def test_time_or_memory_failure_is_not_successful_generation(monkeypatch):
    monkeypatch.setattr(
        service, "guarded_child", lambda *a, **k: (None, {"status": "TERMINATED_RESOURCE_LIMIT"})
    )
    with pytest.raises(ValueError, match="TERMINATED_RESOURCE_LIMIT"):
        service._execute({"operation": "register", "receipts": {}})


def test_cold_registrar_verifies_all_private_sources_under_access_guard(
    private_bundle, designs, history, tmp_path
):
    root, expected = private_bundle
    descriptor = tmp_path / "private-source-designs.json"
    descriptor.write_bytes(
        storage.encode(
            {
                "designs": [asdict(d) for d in designs],
                "history_keys": sorted(history.keys),
                "history_receipt": history.receipt,
                "expected": expected,
            }
        )
    )
    script = r"""
import json,pathlib,sys
from datetime import date
from loometric.prospective_evaluation.storage import install_access_guard
root=pathlib.Path(sys.argv[1]).resolve()
install_access_guard(root,())
from loometric.prospective_evaluation.protocol import CasePlan
from loometric.prospective_evaluation.source import SourceDesign
from loometric.prospective_evaluation.receipts import (
    HistoricalInventory,_register_batch,_verify_ledger,
)
from loometric.synthetic_ml.configuration import GenerationConfig
raw=json.loads(pathlib.Path(sys.argv[2]).read_bytes())
designs=[]
for entry in raw['designs']:
    case=entry['case']
    case['score_dates']=tuple(date.fromisoformat(d) for d in case['score_dates'])
    parameters=entry['configuration']
    parameters['start_date']=date.fromisoformat(parameters['start_date'])
    designs.append(SourceDesign(CasePlan(**case),GenerationConfig(**parameters)))
history=HistoricalInventory(frozenset(tuple(k) for k in raw['history_keys']),raw['history_receipt'])
registered=_register_batch(root,tuple(designs),raw['expected'],history)
assert _verify_ledger(root,tuple(designs),registered['ledger_sha256'],history)['cases']==8
assert not any(n.split('.')[0] in {'pandas','numpy','sklearn','joblib'} for n in sys.modules)
print('Cold label-blind registration and independent verification passed')
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(root), str(descriptor)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Cold label-blind registration" in completed.stdout
