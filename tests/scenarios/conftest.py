from pathlib import Path

import pytest

from loometric.scenarios.loading import load_specification
from loometric.scheduling.loading import load_instance

EXAMPLES = Path(__file__).resolve().parents[2] / "examples/scenarios"


@pytest.fixture
def capacity_baseline():
    return load_instance(EXAMPLES / "capacity-baseline.json")


@pytest.fixture
def workers_spec():
    return load_specification(EXAMPLES / "additional-workers.json")
