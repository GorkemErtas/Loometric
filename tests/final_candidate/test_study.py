"""Complete private source/fit/held-out/reproduction mechanics, never actual EXP-010 seeds."""

import json

import pytest
from test_history_candidate import Foundation
from threadpoolctl import threadpool_limits

from loometric.final_candidate import data, study
from loometric.prospective_evaluation.frozen_models import FrozenModels
from loometric.prospective_evaluation.storage import identity, sha256
from loometric.synthetic_training.data import NUMERIC


@pytest.fixture(scope="module")
def private_execution(tmp_path_factory):
    root = tmp_path_factory.mktemp("private-final") / "source"
    c = data.config()
    c.update(
        {
            "development_seeds": [99111, 99211, 99311, 99411],
            "heldout_seeds": [99511, 99611, 99711, 99811],
            "calendar_days": 35,
            "source_parameters": {"factories": 2, "lines_per_stage": 2, "styles": 3},
            "development_validation_fit_dates": 1,
            "development_validation_embargo_dates": 1,
        }
    )
    c["estimator"].update({"max_iter": 4, "min_samples_leaf": 5})
    profile = {
        "categories": {
            "stage": ["cutting", "sewing", "finishing", "quality_control", "packing"],
            "shift_kind": ["day", "night"],
            "weekday": list("012345"),
        },
        "numeric_bounds": {k: {"minimum": 0, "maximum": 100000} for k in NUMERIC},
        "training_label_minimum": 0,
        "training_label_maximum": 3,
    }
    frozen = FrozenModels(
        {name: Foundation() for name in study.NAMES[:4]}, profile, {"private": True}
    )
    patch = pytest.MonkeyPatch()
    patch.setattr(data, "DIRECTORY", root)
    patch.setattr(data, "config", lambda: c)
    patch.setattr(study, "load_frozen_models", lambda: frozen)
    reads = []
    original = data.read_labels

    def guarded_labels(root, group, case, partition, **kwargs):
        if partition in ("development", "evaluation"):
            folder = "development" if group == "development" else "heldout"
            assert list((root / folder).glob("*.seal.json"))
            assert data.evaluation_labels_enabled.get()
        reads.append((group, case, partition))
        return original(root, group, case, partition, **kwargs)

    patch.setattr(data, "read_labels", guarded_labels)
    with threadpool_limits(limits=1):
        developed = study.develop()
        a = study.evaluate(developed["candidate"]["model_sha256"])
        b = study.evaluate(
            developed["candidate"]["model_sha256"],
            reproduce=True,
            source_receipts=a["source_receipts"],
            expected_report=a["report_sha256"],
        )
    yield root, c, developed, a, b, reads
    patch.undo()


def test_private_complete_study_fits_once_freezes_and_reproduces(private_execution):
    root, c, d, a, b, reads = private_execution
    assert d["candidate"]["estimator_fits"] == 1
    assert d["candidate"]["fit_seeds"] == c["development_seeds"]
    assert a["report_sha256"] == b["report_sha256"] and b["status"] == "REPRODUCED"
    assert sha256((root / "candidate.joblib").read_bytes()) == d["candidate"]["model_sha256"]
    assert (root / "heldout/a.predictions.jsonl").read_bytes() == (
        root / "heldout/b.predictions.jsonl"
    ).read_bytes()
    assert not a["integration"]["eligible_for_experimental_integration"]  # private counts <300
    assert not any(part in ("context", "test", "embargo") for _, _, part in reads)
    assert len(reads) == 32
    assert set(a["macro"]["baseline"]) == set(study.NAMES)


def test_existing_source_and_candidate_tampering_are_rejected(private_execution):
    root, _, d, a, _, _ = private_execution
    case = next(iter(a["source_receipts"]))
    file = root / "heldout" / case / "features.jsonl"
    original = file.read_bytes()
    try:
        file.write_bytes(original + b"\n")
        with pytest.raises(ValueError, match="RECEIPT_DRIFT"):
            data.read_case(root, "heldout", case, a["source_receipts"][case])
    finally:
        file.write_bytes(original)
    with pytest.raises(ValueError, match="CANDIDATE_BYTES_DRIFT"):
        study.load_candidate("0" * 64)
    with pytest.raises(ValueError, match="CREATE_ONLY"):
        study.evaluate(d["candidate"]["model_sha256"])


@pytest.mark.parametrize(
    "mutation", ["extra_outcome", "self_history", "future_time", "other_entity"]
)
def test_rehashed_future_or_entity_join_injection_fails(private_execution, mutation):
    root, _, _, a, _, _ = private_execution
    case = next(iter(a["source_receipts"]))
    directory = root / "heldout" / case
    path = directory / "features.jsonl"
    manifest_path = directory / "manifest.json"
    raw = path.read_bytes()
    old_manifest = manifest_path.read_bytes()
    rows = [json.loads(line) for line in raw.decode().splitlines()]
    row = next(r for r in rows if r["history_sources"])
    if mutation == "extra_outcome":
        row["actual"] = 1
    elif mutation == "self_history":
        row["history_sources"] = [row["local_id"]]
    elif mutation == "future_time":
        row["history_latest_available_at"] = "2099-01-01T00:00:00+00:00"
    else:
        row["context"]["crew_id"] = "other-crew"
    from loometric.prospective_evaluation.storage import encode

    try:
        content = b"".join(encode(r) for r in rows)
        path.write_bytes(content)
        manifest = json.loads(old_manifest)
        manifest["files"][path.name] = identity(content)
        m = encode(manifest)
        manifest_path.write_bytes(m)
        with pytest.raises(ValueError):
            data.read_case(root, "heldout", case, sha256(m))
    finally:
        path.write_bytes(raw)
        manifest_path.write_bytes(old_manifest)
