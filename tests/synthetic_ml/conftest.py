import pytest

from loometric.synthetic_ml.configuration import GenerationConfig
from loometric.synthetic_ml.generation import generate


@pytest.fixture(scope="module")
def synthetic_config():
    return GenerationConfig()


@pytest.fixture(scope="module")
def synthetic_data(synthetic_config):
    return generate(synthetic_config)
