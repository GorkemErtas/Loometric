import json
from pathlib import Path

import pandas as pd
import pytest

import loometric.synthetic_ml.storage as storage
from loometric.ml_research.artifacts import checked_output
from loometric.ml_research.diagnosis import context_projection
from loometric.synthetic_ml.configuration import GenerationConfig
from loometric.synthetic_ml.generation import generate
from loometric.synthetic_ml.storage import digest, encode
from loometric.synthetic_training.data import fingerprint, load_development


def test_research_context_survives_undecodable_reserved_targets(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "OUTPUT_ROOT", tmp_path)
    directory = tmp_path / "fixture"
    config = GenerationConfig()
    receipt = storage.write_bundle(
        generate(config),
        config,
        directory,
        configuration_sha256="a" * 64,
        profile="private-research",
    )
    first = load_development(directory, expected_fingerprint=receipt["manifest_fingerprint"])
    before = context_projection(directory, first)
    manifest = json.loads((directory / "manifest.json").read_bytes())
    for name in ("outcomes.jsonl", "labels.gap.jsonl", "labels.test.jsonl"):
        count = manifest["files"][name]["rows"]
        (directory / name).write_bytes(b"RESERVED_RESEARCH_VALUES_NOT_JSON\n" * count)
        manifest["files"][name]["sha256"] = fingerprint(directory / name)
    manifest["content_fingerprint"] = digest(
        {
            name: manifest["files"][name]
            for name in sorted(manifest["files"])
            if name.endswith(".jsonl")
        }
    )
    (directory / "manifest.json").write_bytes(encode(manifest))
    monkeypatch.setattr(
        "loometric.synthetic_ml.generation.generate",
        lambda *a, **k: pytest.fail("Research regenerated data"),
    )
    after = load_development(directory, expected_fingerprint=digest(manifest))
    pd.testing.assert_frame_equal(first.train.X, after.train.X)
    pd.testing.assert_series_equal(first.validation.y, after.validation.y)
    pd.testing.assert_frame_equal(before, context_projection(directory, after))
    assert not set(before) & set(after.train.X)
    (directory / "features.jsonl").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="CONTEXT_SOURCE_INTEGRITY"):
        context_projection(directory, after)


def test_research_publication_cannot_target_serving_or_historical_paths():
    root = Path(__file__).resolve().parents[2]
    for path in (
        root / "data/processed/experimental_ml/v1",
        root / "data/processed/synthetic_training/new",
        root / "data/raw",
        root / "src/loometric",
    ):
        with pytest.raises(ValueError, match="NEW_IGNORED_RESEARCH"):
            checked_output(path)
