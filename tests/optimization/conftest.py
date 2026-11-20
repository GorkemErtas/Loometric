"""Original frozen synthetic scheduling instances; no ML data/model fixtures."""

from pathlib import Path

import pytest

from loometric.scheduling.loading import load_instance

EXAMPLES = Path(__file__).resolve().parents[2] / "examples/scheduling"


@pytest.fixture
def optimization_instance():
    return load_instance(EXAMPLES / "competition.json")
