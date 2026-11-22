import copy
import json
from pathlib import Path

import pytest

from loometric.synthetic_training.configuration import load_study

ROOT = Path(__file__).resolve().parents[2]


def test_predeclared_search_and_receipts_are_complete():
    config = load_study(ROOT / "configs/synthetic_training_v1.json")
    assert len(config["search"]) == 6 and len(config["datasets"]) == 10
    assert len({d["expected_manifest_fingerprint"] for d in config["datasets"]}) == 10
    assert config["selection"]["minimum_macro_improvement_percent"] == 5


@pytest.mark.parametrize(
    "kind", ["version", "resource", "leaky_fold", "unknown_field", "missing_world"]
)
def test_study_drift_or_unbounded_search_is_rejected(tmp_path, kind):
    config = copy.deepcopy(load_study(ROOT / "configs/synthetic_training_v1.json"))
    if kind == "version":
        config["policy_version"] = "unreviewed"
    elif kind == "resource":
        config["search"][2]["parameters"]["n_estimators"] = 100000
    elif kind == "leaky_fold":
        config["folds"]["purged_dates"] = 0
    elif kind == "unknown_field":
        config["actual_productivity"] = True
    else:
        config["datasets"].pop()
    path = tmp_path / "study.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError):
        load_study(path)
