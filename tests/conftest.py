"""Small synthetic records only; tests never substitute for the real dataset profile."""

from pathlib import Path

import pandas as pd
import pytest

from loometric.data.loading import clean_data
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


@pytest.fixture
def chronological_data(raw_data: pd.DataFrame) -> pd.DataFrame:
    """Ten dates with two departments; separate from all actual experiment findings."""
    records = []
    for number, date in enumerate(pd.date_range("2015-01-01", periods=10)):
        for department in range(2):
            record = raw_data.iloc[department].copy()
            record["date"] = date.strftime("%m/%d/%Y")
            record["day"] = date.day_name()
            record["actual_productivity"] = str(0.3 + number * 0.02 + department * 0.2)
            records.append(record)
    return clean_data(pd.DataFrame(records, dtype="string").reset_index(drop=True))


@pytest.fixture
def chronological_csv(tmp_path: Path, chronological_data: pd.DataFrame) -> Path:
    raw = chronological_data.copy(deep=True)
    raw["date"] = raw["date"].dt.strftime("%m/%d/%Y")
    path = tmp_path / "synthetic-chronological.csv"
    raw.to_csv(path, index=False)
    return path
