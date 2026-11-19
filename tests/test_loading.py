from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from loometric.data.loading import DatasetReadError, clean_data, read_csv


def test_loading_normalizes_a_copy_and_keeps_raw_bytes(dataset_path: Path) -> None:
    original_bytes = dataset_path.read_bytes()
    raw = read_csv(dataset_path)
    original_frame = raw.copy(deep=True)
    clean = clean_data(raw)

    assert_frame_equal(raw, original_frame)
    assert dataset_path.read_bytes() == original_bytes
    assert set(clean["department"]) == {"sewing", "finishing"}
    assert clean["wip"].isna().tolist() == [False, True, False, True]
    assert clean["no_of_workers"].iloc[0] == 10.5


def test_ambiguous_date_is_explicitly_month_first(raw_data: pd.DataFrame) -> None:
    clean = clean_data(raw_data)
    assert clean["date"].iloc[2] == pd.Timestamp("2015-01-02")


@pytest.mark.parametrize("date", ["13/01/2015", "2015-01-02", "02/30/2015", "tomorrow"])
def test_invalid_or_different_date_formats_are_not_guessed(
    raw_data: pd.DataFrame, date: str
) -> None:
    raw_data.loc[0, "date"] = date
    assert pd.isna(clean_data(raw_data).loc[0, "date"])


@pytest.mark.parametrize(
    "content",
    [
        "",
        "a,a\n1,2\n",
        ",b\n1,2\n",
        "a,b\n1\n",
        "a,b\n1,2,3\n",
        'a,b\n"unfinished,2',
    ],
)
def test_malformed_csv_is_rejected(tmp_path: Path, content: str) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(DatasetReadError):
        read_csv(path)


def test_utf8_bom_is_supported(tmp_path: Path) -> None:
    path = tmp_path / "bom.csv"
    path.write_text("date,team\n01/01/2015,1\n", encoding="utf-8-sig")
    assert read_csv(path).columns.tolist() == ["date", "team"]


def test_projection_and_source_row_selection(dataset_path: Path) -> None:
    projected = read_csv(dataset_path, columns=("date",), row_indices=frozenset({1, 3}))
    assert projected.columns.tolist() == ["date"]
    assert projected["date"].tolist() == ["01/01/2015", "01/02/2015"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"columns": ("missing",)},
        {"columns": ("date", "date")},
        {"row_indices": frozenset({-1})},
        {"row_indices": frozenset({999})},
    ],
)
def test_invalid_projection_rejected(dataset_path: Path, kwargs: dict) -> None:
    with pytest.raises(DatasetReadError):
        read_csv(dataset_path, **kwargs)


def test_unselected_rows_still_receive_structural_checks(tmp_path: Path) -> None:
    path = tmp_path / "ragged-outer.csv"
    path.write_text("date,team\n01/01/2015,1\n01/02/2015\n", encoding="utf-8")
    with pytest.raises(DatasetReadError):
        read_csv(path, columns=("date",), row_indices=frozenset({0}))
