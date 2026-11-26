"""Shared private mechanical sources; production EXP-009 seeds are forbidden here."""

import copy
import shutil
from datetime import date

import pytest

from loometric.prospective_evaluation import generation, receipts, storage
from loometric.prospective_evaluation.protocol import CasePlan
from loometric.prospective_evaluation.source import SourceDesign
from loometric.synthetic_ml.configuration import GenerationConfig
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
