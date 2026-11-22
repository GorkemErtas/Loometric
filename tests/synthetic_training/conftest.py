import pytest

import loometric.synthetic_ml.storage as storage
from loometric.synthetic_ml.configuration import GenerationConfig
from loometric.synthetic_ml.generation import generate


@pytest.fixture
def training_bundle(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "OUTPUT_ROOT", tmp_path / "data")
    directory = tmp_path / "data" / "fixture"
    config = GenerationConfig()
    receipt = storage.write_bundle(
        generate(config), config, directory, configuration_sha256="c" * 64, profile="development"
    )
    return directory, receipt["manifest_fingerprint"]
