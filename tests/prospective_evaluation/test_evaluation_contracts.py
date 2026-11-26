"""Private receipt, access-control and predeclared acceptance boundary fixtures."""

import json
import subprocess
import sys
from dataclasses import asdict

import pytest

from loometric.prospective_evaluation import (
    acceptance,
    diagnostics,
    evaluator,
    frozen_models,
    storage,
)
from loometric.prospective_evaluation.protocol import load_protocol


@pytest.fixture
def model_bundle(tmp_path):
    config = load_protocol()
    profile = {"private": "profile"}
    metadata = {
        "v1": {
            "support": profile,
            "training": {"source": {"train_fingerprint": "private-fingerprint"}},
            "models": {m["name"]: {"identity": m["identity"]} for m in config["models"][:3]},
            "feature_order": config["contract"]["feature_columns"],
            "target": config["contract"]["target"],
            "promotion_decision": "NO_ML_PROMOTION",
        },
        "v2": {
            "feature_order": config["contract"]["feature_columns"],
            "target": config["contract"]["target"],
            "promotion_decision": "NO_ML_PROMOTION",
        },
    }
    config["evaluation"]["support_profile_sha256"] = storage.sha256(storage.encode(profile))
    config["evaluation"]["training_fingerprint"] = "private-fingerprint"
    for name, bundle in config["frozen_bundles"].items():
        bundle["directory"] = f"private/{name}"
        directory = tmp_path / bundle["directory"]
        directory.mkdir(parents=True)
        for filename in bundle["files"]:
            value = (
                storage.encode(metadata[name])
                if filename == "metadata.json"
                else b"PRIVATE_NOT_AN_EXECUTABLE_MODEL"
            )
            (directory / filename).write_bytes(value)
            bundle["files"][filename] = storage.sha256(value)
        manifest = {"files": bundle["files"], "promotion_decision": "NO_ML_PROMOTION"}
        content = storage.encode(manifest)
        (directory / "manifest.json").write_bytes(content)
        bundle["manifest_sha256"] = storage.sha256(content)
    return tmp_path, config, metadata


@pytest.mark.parametrize(
    "bundle,file",
    [
        ("v1", "manifest.json"),
        ("v1", "metadata.json"),
        ("v1", "grouped_mean.json"),
        ("v1", "random_forest.joblib"),
        ("v1", "histogram_gradient_boosting.joblib"),
        ("v2", "manifest.json"),
        ("v2", "metadata.json"),
        ("v2", "rf_physics.joblib"),
        ("v1", "extra.json"),
    ],
)
def test_every_model_file_is_pinned_and_closed(model_bundle, bundle, file):
    repository, config, _ = model_bundle
    directory = repository / config["frozen_bundles"][bundle]["directory"]
    (directory / file).write_bytes(b"TAMPERED")
    with pytest.raises(ValueError):
        frozen_models.verify_model_receipts(config, repository)


@pytest.mark.parametrize("field", ["support_profile_sha256", "training_fingerprint"])
def test_model_support_and_training_identity_are_mandatory(model_bundle, field):
    repository, config, _ = model_bundle
    config["evaluation"][field] = "0" * 64
    with pytest.raises(ValueError, match="CONTRACT_DRIFT"):
        frozen_models.verify_model_receipts(config, repository)


def test_all_bundles_verified_before_existing_trusted_loaders(model_bundle, monkeypatch):
    repository, config, metadata = model_bundle
    from loometric.experimental_ml import artifacts as v1
    from loometric.experimental_ml_v2 import artifacts as v2

    monkeypatch.setattr(frozen_models, "load_protocol", lambda: config)
    monkeypatch.setattr(frozen_models, "verify_frozen_sources", lambda c: None)
    check = frozen_models.verify_model_receipts
    monkeypatch.setattr(frozen_models, "verify_model_receipts", lambda c: check(c, repository))
    calls = []

    def load_v1(receipt):
        assert receipt == config["frozen_bundles"]["v1"]["manifest_sha256"]
        calls.append("v1")
        return metadata["v1"], {m["name"]: object() for m in config["models"][:3]}

    def load_v2():
        calls.append("v2")
        return metadata["v2"], object()

    monkeypatch.setattr(v1, "load_trusted", load_v1)
    monkeypatch.setattr(v2, "load_trusted_offline", load_v2)
    result = frozen_models.load_frozen_models()
    assert len(result.models) == 4 and calls == ["v1", "v2"]
    calls.clear()
    (repository / config["frozen_bundles"]["v2"]["directory"] / "rf_physics.joblib").write_bytes(
        b"untrusted"
    )
    with pytest.raises(ValueError):
        frozen_models.load_frozen_models()
    assert not calls


@pytest.fixture
def passing_evidence(designs):
    """Deliberately mechanical aggregate evidence; no model or generated outcome used."""
    cells = {}
    for design in designs:
        models = {}
        for name, value in (
            ("grouped_mean", 1.0),
            ("random_forest", 1.0),
            ("histogram_gradient_boosting", 1.0),
            ("rf_physics", 0.9),
        ):
            metrics = {m: value for m in diagnostics.METRICS}
            models[name] = {
                "metrics": metrics,
                "defined_target_counts": {"rows": 360, "dates": 18},
                "subgroups": {
                    "stage": {
                        s.value: {
                            "metrics": metrics.copy(),
                            "defined_target_counts": {
                                "rows": 72,
                                "dates": 18,
                                "lines": 2,
                                "crews": 4,
                            },
                        }
                        for s in diagnostics.Stage
                    }
                },
            }
        cells[design.case.case_id] = {"models": models}
    compared = {
        "primary": {
            "individual_worlds": {d.case.world_id: -0.1 for d in designs},
            "interval": [-0.1, -0.1],
        }
    }
    return cells, compared


def test_passing_evidence_is_only_replication_and_requires_reproduction(passing_evidence, designs):
    cells, compared = passing_evidence
    result = acceptance.evaluate_acceptance(cells, designs, compared, load_protocol())
    assert result["provisional_status"] == "FROZEN_CANDIDATE_REPLICATION_SUPPORTED"
    assert result["requires_verified_reproduction"] is True
    assert result["promotion_decision"] == "NO_ML_PROMOTION"


@pytest.mark.parametrize(
    "guard",
    [
        "stage",
        "p95_absolute_error",
        "p95_positive_error",
        "worst_absolute_error",
        "baseline_macro_gain_group",
        "baseline_macro_gain_forest",
        "world_forest",
        "world_wins",
        "primary_interval",
        "disruption_macro",
        "disruption_seed",
    ],
)
def test_each_declared_numerical_guard_can_fail_without_pooled_rescue(
    passing_evidence, designs, guard
):
    cells, compared = passing_evidence
    first = cells[designs[0].case.case_id]["models"]
    if guard == "stage":
        first["rf_physics"]["subgroups"]["stage"]["sewing"]["metrics"]["mae"] = 1.051
    elif guard in ("p95_absolute_error", "p95_positive_error", "worst_absolute_error"):
        first["rf_physics"]["metrics"][guard] = 1.2
    elif guard in ("baseline_macro_gain_group", "baseline_macro_gain_forest"):
        reference = "grouped_mean" if guard.endswith("group") else "random_forest"
        for design in designs:
            if design.case.condition == "baseline":
                cells[design.case.case_id]["models"][reference]["metrics"]["mae"] = 0.91
    elif guard == "world_forest":
        first["rf_physics"]["metrics"]["mae"] = 1.051
    elif guard == "world_wins":
        compared["primary"]["individual_worlds"] = {d.case.world_id: 0 for d in designs}
    elif guard == "primary_interval":
        compared["primary"]["interval"][1] = 0
    elif guard == "disruption_macro":
        for design in designs:
            if design.case.condition == "disruption":
                cells[design.case.case_id]["models"]["rf_physics"]["metrics"]["mae"] = 1.001
    else:
        cells[designs[1].case.case_id]["models"]["rf_physics"]["metrics"]["mae"] = 1.101
    result = acceptance.evaluate_acceptance(cells, designs, compared, load_protocol())
    assert result["provisional_status"] == "REPLICATION_NOT_SUPPORTED"
    assert not all(c["passed"] for c in result["numerical_guards"].values())


@pytest.mark.parametrize(
    "level,field,value",
    [
        ("case", "rows", 299),
        ("case", "dates", 14),
        ("stage", "rows", 49),
        ("stage", "dates", 14),
        ("stage", "lines", 1),
        ("stage", "crews", 3),
    ],
)
def test_every_minimum_sample_guard_is_inconclusive(passing_evidence, designs, level, field, value):
    cells, compared = passing_evidence
    model = cells[designs[0].case.case_id]["models"]["grouped_mean"]
    target = model if level == "case" else model["subgroups"]["stage"]["sewing"]
    target["defined_target_counts"][field] = value
    assert (
        acceptance.evaluate_acceptance(cells, designs, compared, load_protocol())[
            "provisional_status"
        ]
        == "INCONCLUSIVE"
    )


@pytest.mark.parametrize(
    "counters,code",
    [
        ({"calls": 32, "predictions": 0}, "PREDICT_CALL_BUDGET"),
        ({"calls": 0, "predictions": 11520}, "PREDICTION_COUNT_BUDGET"),
    ],
)
def test_budgets_reject_work_before_estimator_call(designs, counters, code):
    from types import SimpleNamespace

    rows = evaluator.feature_observations(
        designs[0], evaluator.expected_source(designs[0].configuration)
    )

    class NeverPredict:
        def predict(self, frame):
            pytest.fail("Budget was not checked first")

    models = SimpleNamespace(models={str(i): NeverPredict() for i in range(4)})
    with pytest.raises(ValueError, match=code):
        evaluator._infer_case(rows, models, counters, load_protocol()["budget"])


def test_cold_guarded_private_evaluation_and_reserved_access(
    private_bundle, designs, history, tmp_path
):
    from loometric.prospective_evaluation.receipts import _register_batch

    root, expected = private_bundle
    registration = _register_batch(root, designs, expected, history)
    descriptor = tmp_path / "private-evaluation-descriptor.json"
    descriptor.write_bytes(
        storage.encode(
            {
                "designs": [asdict(d) for d in designs],
                "history_keys": sorted(history.keys),
                "history_receipt": history.receipt,
                "ledger": registration["ledger_sha256"],
            }
        )
    )
    script = r"""
import json,pathlib,sys,os
from datetime import date
sys.dont_write_bytecode=True
root=pathlib.Path(sys.argv[1]).resolve()
raw=json.loads(pathlib.Path(sys.argv[2]).read_bytes())
from loometric.prospective_evaluation.protocol import CasePlan
from loometric.prospective_evaluation.source import SourceDesign
from loometric.prospective_evaluation.receipts import HistoricalInventory
designs=[]
for entry in raw['designs']:
    case=entry['case']
    case['score_dates']=tuple(date.fromisoformat(d) for d in case['score_dates'])
    parameters=entry['configuration']
    parameters['start_date']=date.fromisoformat(parameters['start_date'])
    designs.append(SourceDesign(CasePlan(**case),GenerationConfig(**parameters)))
"""
    # Import the unchanged configuration class before constructing private descriptors.
    script = script.replace(
        "designs=[]",
        "from loometric.synthetic_ml.configuration import GenerationConfig\ndesigns=[]",
    )
    script += r"""
history=HistoricalInventory(frozenset(tuple(k) for k in raw['history_keys']),raw['history_receipt'])
from loometric.prospective_evaluation.evaluation_access import install_evaluation_guard
install_evaluation_guard(root,root/'runs/a',(),set())
from loometric.prospective_evaluation.evaluator import _evaluate
from loometric.prospective_evaluation.frozen_models import FrozenModels
from loometric.prospective_evaluation.storage import opaque_identity
from loometric.synthetic_training.data import NUMERIC
import numpy as np
class PrivatePredictor:
    def fit(self,*a,**k): raise AssertionError('fit is forbidden')
    def predict(self,X): return np.full(len(X),.8)
names=['grouped_mean','random_forest','histogram_gradient_boosting','rf_physics']
profile={'categories':{'stage':['cutting','sewing','finishing','quality_control','packing'],
                      'shift_kind':['day','night'],'weekday':list('012345')},
         'numeric_bounds':{c:{'minimum':0,'maximum':100000} for c in NUMERIC},
         'training_label_minimum':0,'training_label_maximum':2}
models=FrozenModels({n:PrivatePredictor() for n in names},profile,{'private':True})
case=root/'datasets'/designs[0].case.case_id
for name in ['outcomes.jsonl','labels.train.jsonl','labels.gap.jsonl',
             'labels.test.jsonl','labels.validation.jsonl']:
    try: (case/name).read_bytes()
    except PermissionError: pass
    else: raise AssertionError('unguarded label access: '+name)
    assert opaque_identity(case/name)['rows']>=0
try: (root/'untrusted.joblib').read_bytes()
except PermissionError: pass
else: raise AssertionError('untrusted model access')
result=_evaluate(root,tuple(designs),history,raw['ledger'],lambda:models)
assert result['decision']=='PENDING_REPRODUCTION'
for action in [lambda:(case/'features.jsonl').write_bytes(b'overwrite'),
               lambda:(root/'runs/a/report.json').write_bytes(b'overwrite'),
               lambda:(case/'features.jsonl').unlink(),
               lambda:os.rename(case/'features.jsonl',case/'changed.jsonl')]:
    try: action()
    except PermissionError: pass
    else: raise AssertionError('mutation was accepted')
try: (case/'labels.validation.jsonl').read_bytes()
except PermissionError: pass
else: raise AssertionError('validation capability escaped its reader')
print('Private guarded evaluation sealed; reserved reads and mutations denied')
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(root), str(descriptor)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Private guarded evaluation sealed" in completed.stdout


def test_real_evaluation_worker_is_bounded_and_rejects_unknown_operation(preserve_actual_sources):
    from loometric.execution import guarded_child

    payload, measured = guarded_child(
        json.dumps({"operation": "forbidden"}),
        2048,
        20,
        worker_module="loometric.prospective_evaluation.evaluation_worker",
    )
    assert payload["error"]["code"] == "UNSUPPORTED_EVALUATION_OPERATION", measured
    assert payload["status"] == "INVALID_EVALUATION"
    assert payload["promotion_decision"] == "NO_ML_PROMOTION"
    preserve_actual_sources()


def test_real_evaluation_worker_deadline_stops_the_whole_process():
    from loometric.execution import guarded_child

    payload, measured = guarded_child(
        json.dumps({"operation": "forbidden"}),
        2048,
        0.001,
        worker_module="loometric.prospective_evaluation.evaluation_worker",
    )
    assert payload is None and measured["status"] == "TERMINATED_RESOURCE_LIMIT"
