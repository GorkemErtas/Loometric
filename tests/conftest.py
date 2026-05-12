"""Small synthetic records only; tests never substitute for the real dataset profile."""

from pathlib import Path

import pandas as pd
import pytest

from loometric.data.schema import COLUMNS


@pytest.fixture
def raw_data() -> pd.DataFrame:
    common = {
        "date": "01/01/2015",
        "quarter": "Quarter1",
        "department": "sweing",
        "day": "Thursday",
        "team": "1",
        "targeted_productivity": "0.8",
        "smv": "22",
        "wip": "100",
        "over_time": "120",
        "incentive": "10",
        "idle_time": "0",
        "idle_men": "0",
        "no_of_style_change": "0",
        "no_of_workers": "10.5",
        "actual_productivity": "0.8",
    }
    records = [
        common,
        {
            **common,
            "department": "finishing ",
            "team": "2",
            "wip": "",
            "actual_productivity": "0.75",
        },
        {
            **common,
            "date": "01/02/2015",
            "day": "Friday",
            "wip": "90",
            "actual_productivity": "0.6",
        },
        {
            **common,
            "date": "01/02/2015",
            "day": "Friday",
            "department": "finishing ",
            "team": "2",
            "wip": "",
            "actual_productivity": "1.05",
        },
    ]
    return pd.DataFrame(records, columns=COLUMNS, dtype="string")


@pytest.fixture
def dataset_path(tmp_path: Path, raw_data: pd.DataFrame) -> Path:
    path = tmp_path / "synthetic.csv"
    raw_data.to_csv(path, index=False)
    return path
