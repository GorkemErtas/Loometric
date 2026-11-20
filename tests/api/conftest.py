from pathlib import Path
from secrets import token_urlsafe

import pytest
from pydantic import SecretStr

from loometric.api.settings import Settings
from loometric.planning.loading import parse_json

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


@pytest.fixture
def api_settings():
    return Settings(token=SecretStr(token_urlsafe(32)))


@pytest.fixture
def fixture_json():
    def load(name):
        return parse_json((EXAMPLES / name).read_text(encoding="utf-8"))

    return load
