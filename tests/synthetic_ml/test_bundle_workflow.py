import hashlib
import json

import pytest

import loometric.synthetic_ml.storage as storage
from loometric.synthetic_ml.cli import main
from loometric.synthetic_ml.features import build_features
from loometric.synthetic_ml.storage import digest, encode, read_bundle, write_bundle


@pytest.fixture
def bundle(synthetic_data, synthetic_config, tmp_path, monkeypatch):
    root = tmp_path / "synthetic"
    monkeypatch.setattr(storage, "OUTPUT_ROOT", root)
    output = root / "dataset"
    receipt = write_bundle(
        synthetic_data,
        synthetic_config,
        output,
        configuration_sha256="c" * 64,
        profile="synthetic-test-fixture",
    )
    return output, receipt


def test_roundtrip_exact_serialization_replay_and_no_overwrite(
    bundle, synthetic_data, synthetic_config
):
    output, receipt = bundle
    loaded, config = read_bundle(output, expected_fingerprint=receipt["manifest_fingerprint"])
    assert loaded == synthetic_data and config == synthetic_config
    originals = {p.name: p.read_bytes() for p in output.iterdir()}
    manifest = json.loads(originals["manifest.json"])
    assert manifest["synthetic"] is True
    assert all(
        isinstance(json.loads(line)["worker_minutes_per_piece"], str)
        for line in originals["standards.jsonl"].splitlines()
    )
    assert json.loads(originals["quality.json"])["replay_verified"] is True
    assert "standard_capacity_attainment" not in next(iter(build_features(loaded)))["inputs"]
    with pytest.raises(ValueError, match="already exists"):
        write_bundle(
            loaded, config, output, configuration_sha256="c" * 64, profile="synthetic-test-fixture"
        )
    assert originals == {p.name: p.read_bytes() for p in output.iterdir()}
    other = output.parent / "second"
    assert (
        write_bundle(
            loaded, config, other, configuration_sha256="c" * 64, profile="synthetic-test-fixture"
        )
        == receipt
    )
    assert originals == {p.name: p.read_bytes() for p in other.iterdir()}


@pytest.mark.parametrize(
    "kind", ["file_drift", "receipt_drift", "extra_table_field", "leaked_feature"]
)
def test_corruption_or_leaked_derived_features_fail_closed(bundle, kind):
    output, receipt = bundle
    expected = receipt["manifest_fingerprint"]
    manifest = json.loads((output / "manifest.json").read_text())
    if kind == "receipt_drift":
        expected = "0" * 64
    elif kind == "file_drift":
        with (output / "outcomes.jsonl").open("ab") as destination:
            destination.write(b" ")
    else:
        name = "plans.jsonl" if kind == "extra_table_field" else "features.jsonl"
        records = [json.loads(line) for line in (output / name).read_text().splitlines()]
        if kind == "extra_table_field":
            records[0]["actual_productivity"] = "forbidden target"
        else:
            records[0]["inputs"]["completed_good_pieces"] = 100
        content = b"".join(encode(r) for r in records)
        (output / name).write_bytes(content)
        manifest["files"][name]["sha256"] = hashlib.sha256(content).hexdigest()
        (output / "manifest.json").write_bytes(encode(manifest))
        expected = digest(manifest)  # Newly retained receipt still cannot admit a leaked view.
    with pytest.raises(ValueError):
        read_bundle(output, expected_fingerprint=expected)


def test_output_cannot_escape_ignored_dataset_root(synthetic_data, synthetic_config, tmp_path):
    with pytest.raises(ValueError, match="under data/processed/synthetic_ml"):
        write_bundle(
            synthetic_data,
            synthetic_config,
            tmp_path / "unapproved",
            configuration_sha256="c" * 64,
            profile="test",
        )
    assert not (tmp_path / "unapproved").exists()


def test_cli_generation_receipt_and_readonly_audit(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(storage, "OUTPUT_ROOT", tmp_path / "datasets")
    output = tmp_path / "datasets" / "first"
    assert main(["generate", "--output", str(output)]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert (
        main(
            [
                "audit",
                "--dataset",
                str(output),
                "--expected-fingerprint",
                receipt["manifest_fingerprint"],
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["replay_verified"] is True
    assert report["reserved_test_target_statistics"] == "NOT_COMPUTED"
    originals = {p.name: p.read_bytes() for p in output.iterdir()}
    assert main(["generate", "--output", str(output)]) == 2
    assert originals == {p.name: p.read_bytes() for p in output.iterdir()}
    capsys.readouterr()
    assert (
        main(["generate", "--scenario", "fabricated_factory_secret", "--output", str(output)]) == 2
    )
    assert "fabricated_factory_secret" not in capsys.readouterr().err
