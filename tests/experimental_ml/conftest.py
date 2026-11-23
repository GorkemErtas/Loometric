import pandas as pd
import pytest
from threadpoolctl import threadpool_limits

import loometric.synthetic_ml.storage as storage
from loometric.experimental_ml.constants import MODELS, ROOT, STUDY_CASE
from loometric.experimental_ml.publish import publish_models
from loometric.synthetic_ml.configuration import GenerationConfig
from loometric.synthetic_ml.generation import generate
from loometric.synthetic_training.configuration import load_study
from loometric.synthetic_training.data import load_development
from loometric.synthetic_training.metrics import analyze
from loometric.synthetic_training.models import build_model
from loometric.synthetic_training.risk import residual_reference


@pytest.fixture(scope="module")
def publication_fixture(tmp_path_factory):
    root = tmp_path_factory.mktemp("experimental")
    patch = pytest.MonkeyPatch()
    patch.setattr(storage, "OUTPUT_ROOT", root)
    config = GenerationConfig(calendar_days=35, factories=2, styles=3)
    source = root / "source"
    receipt = storage.write_bundle(
        generate(config), config, source, configuration_sha256="a" * 64, profile="private-test"
    )
    # The fixture generator can construct private tests. The publisher's reader
    # must not decode their reserved/gap/global-outcome target values.
    data = load_development(source, expected_fingerprint=receipt["manifest_fingerprint"])
    study = load_study(ROOT / "configs/synthetic_training_v1.json")
    specs = {s["name"]: s for s in study["search"]}
    specs["grouped_mean"] = {"name": "grouped_mean", "family": "naive", "parameters": {}}
    report = {
        "configuration": study,
        "selection": {"status": "NO_ML_PROMOTION"},
        "reserved_label_values_decoded": False,
        "final_test_evaluated": False,
        "datasets": {STUDY_CASE: {"provenance": data.provenance}},
        "validation": {STUDY_CASE: {}},
        "residual_references": {STUDY_CASE: {}},
    }
    rows = []
    with threadpool_limits(limits=1):
        for name in MODELS.values():
            model = build_model(specs[name], 42).fit(data.train.X, data.train.y)
            predicted = pd.Series(model.predict(data.validation.X), index=data.validation.X.index)
            report["validation"][STUDY_CASE][name] = analyze(
                data.validation.y, predicted, data.validation.metadata
            )
            # Private fixture residuals are only mechanical test data; actual
            # production metadata uses retained benchmark training-OOF residuals.
            report["residual_references"][STUDY_CASE][name] = residual_reference(
                [{"stage": "cutting", "actual": 0.4, "prediction": 0.5}]
            )
            rows.extend(
                {
                    "case": STUDY_CASE,
                    "model": name,
                    "observation_id": oid,
                    "prediction": float(value),
                }
                for oid, value in predicted.items()
            )
    output = root / "models"
    result = publish_models(data, report, rows, output)
    yield {
        "directory": output,
        "receipt": result["manifest_sha256"],
        "result": result,
        "data": data,
        "report": report,
        "rows": rows,
        "root": root,
    }
    patch.undo()


@pytest.fixture
def private_bundle(publication_fixture, tmp_path):
    import shutil

    directory = tmp_path / "models"
    shutil.copytree(publication_fixture["directory"], directory)
    return directory, publication_fixture["receipt"]
