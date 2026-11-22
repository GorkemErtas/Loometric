import hashlib
import json
from decimal import Decimal

import pandas as pd
import pytest

import loometric.synthetic_training.data as loading
from loometric.synthetic_ml.features import FEATURE_COLUMNS
from loometric.synthetic_ml.storage import digest, encode
from loometric.synthetic_training.data import exact_float, load_development


def rebind(directory):
    manifest = json.loads((directory / "manifest.json").read_text())
    for name, identity in manifest["files"].items():
        content = (directory / name).read_bytes()
        identity["sha256"] = hashlib.sha256(content).hexdigest()
        if name.endswith(".jsonl"):
            identity["rows"] = content.count(b"\n")
    manifest["content_fingerprint"] = digest(
        {name: identity for name, identity in manifest["files"].items() if name.endswith(".jsonl")}
    )
    (directory / "manifest.json").write_bytes(encode(manifest))
    return digest(manifest)


def test_receipt_conversion_order_and_audited_undefined_labels(training_bundle):
    directory, expected = training_bundle
    data = load_development(directory, expected_fingerprint=expected)
    assert tuple(data.train.X.columns) == FEATURE_COLUMNS
    assert len(data.train.X) == 532 and len(data.validation.X) == 178
    assert len(data.train.excluded) == 8 and len(data.validation.excluded) == 2
    assert all(r["prediction_attempted"] is False for r in data.train.excluded)
    assert data.audit["reserved_labels_decoded"] is False
    assert data.audit["label_files_decoded"] == ["labels.train.jsonl", "labels.validation.jsonl"]
    assert max(data.train.metadata.label_available_at) < min(data.validation.metadata.cutoff)
    assert data.train.y.gt(1).any()
    assert not {"seed", "scenario", "population", "factory_id", "crew_id", "observation_id"} & set(
        data.train.X
    )
    assert data.provenance["manifest_fingerprint"] == expected
    assert exact_float(Decimal("1.234567890123456789")) == pytest.approx(1.2345678901234567)


def test_reserved_and_gap_values_are_opaque_even_when_not_valid_json(training_bundle, monkeypatch):
    directory, receipt = training_bundle
    before = load_development(directory, expected_fingerprint=receipt)
    for name in ("outcomes.jsonl", "labels.gap.jsonl", "labels.test.jsonl"):
        count = (directory / name).read_bytes().count(b"\n")
        (directory / name).write_bytes(b"RESERVED_LABEL_MUST_NOT_BE_DECODED\n" * count)
    (directory / "quality.json").write_bytes(b"REPORT_NOT_AN_INPUT\n")
    receipt = rebind(directory)
    original = loading._json_rows

    def guard(path):
        assert path.name not in {
            "outcomes.jsonl",
            "labels.gap.jsonl",
            "labels.test.jsonl",
            "quality.json",
        }
        yield from original(path)

    monkeypatch.setattr(loading, "_json_rows", guard)
    after = load_development(directory, expected_fingerprint=receipt)
    pd.testing.assert_frame_equal(before.train.X, after.train.X)
    pd.testing.assert_series_equal(before.train.y, after.train.y)
    pd.testing.assert_series_equal(before.validation.y, after.validation.y)
    assert before.provenance["train_fingerprint"] == after.provenance["train_fingerprint"]


def test_mismatch_fails_before_any_record_decoding(training_bundle, monkeypatch):
    directory, receipt = training_bundle
    (directory / "features.jsonl").write_bytes(b"tampered\n")

    def prohibited(*args):
        raise AssertionError("No source values may be decoded before complete byte verification")

    monkeypatch.setattr(loading, "_json_rows", prohibited)
    with pytest.raises(ValueError, match="DIGEST"):
        load_development(directory, expected_fingerprint=receipt)
    with pytest.raises(ValueError, match="RECEIPT"):
        load_development(directory, expected_fingerprint="a" * 64)


@pytest.mark.parametrize(
    "kind", ["feature_leak", "partition", "target", "null_status", "cutoff", "timestamp"]
)
def test_semantic_drift_rejected_even_with_a_new_receipt(training_bundle, kind):
    directory, _ = training_bundle
    name = (
        "features.jsonl"
        if kind == "feature_leak"
        else "membership.jsonl"
        if kind == "partition"
        else "plans.jsonl"
        if kind == "cutoff"
        else "labels.train.jsonl"
    )
    rows = [json.loads(line) for line in (directory / name).read_text().splitlines()]
    row = rows[0]
    if kind == "feature_leak":
        row["inputs"]["completed_good_pieces"] = 200
    elif kind == "partition":
        row["partition"] = "test"
    elif kind == "target":
        row["standard_capacity_attainment"] = "0.12345"
    elif kind == "null_status":
        row["status"] = "ZERO_PLANNED_CAPACITY"
    elif kind == "cutoff":
        row["snapshot_at"] = "2030-01-08T10:00:00+03:00"
    else:
        row["available_at"] = "2030-01-01T00:00:00+03:00"
    (directory / name).write_bytes(b"".join(encode(row) for row in rows))
    receipt = rebind(directory)
    with pytest.raises(ValueError):
        load_development(directory, expected_fingerprint=receipt)


@pytest.mark.parametrize("value", [1.25, "0.8", Decimal("NaN"), Decimal("Infinity"), 10**100])
def test_invalid_numeric_source_is_not_coerced_or_imputed(value):
    with pytest.raises((ValueError, OverflowError)):
        exact_float(value)
