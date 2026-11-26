"""Mechanical fixtures must never create or modify actual final experiment outputs."""

import pytest

from loometric.prospective_evaluation.protocol import ROOT


@pytest.fixture(autouse=True)
def preserve_actual_final_outputs():
    root = ROOT / "data/processed/final_candidate/exp-010"

    def snapshot():
        return (
            {
                str(p.relative_to(root)): (p.stat().st_size, p.stat().st_mtime_ns)
                for p in (root, *root.rglob("*"))
            }
            if root.exists()
            else None
        )

    before = snapshot()
    yield
    assert snapshot() == before, "Private tests modified actual final experiment outputs"
