from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from loometric.data.loading import load_validated_csv
from loometric.data.profiling import fingerprint
from loometric.data.splitting import (
    apply_split_config,
    load_split_config,
    main,
    make_split_config,
    save_split_config,
)

DIGEST = "a" * 64


def test_complete_dates_have_strict_boundaries_and_all_rows_once(
    chronological_data: pd.DataFrame,
) -> None:
    source = chronological_data.iloc[::-1].copy()
    original = source.copy(deep=True)
    config = make_split_config(source, DIGEST)
    splits = apply_split_config(source, config, dataset_sha256=DIGEST)
    assert_frame_equal(source, original)
    assert [
        config.train.distinct_dates,
        config.validation.distinct_dates,
        config.test.distinct_dates,
    ] == [6, 2, 2]
    assert [len(splits.train), len(splits.validation), len(splits.test)] == [12, 4, 4]
    assert splits.train["date"].max() < splits.validation["date"].min()
    assert splits.validation["date"].max() < splits.test["date"].min()
    combined = pd.concat([splits.train, splits.validation, splits.test])
    assert combined.index.is_unique
    assert_frame_equal(
        combined.reset_index(drop=True),
        source.sort_values("date", kind="stable").reset_index(drop=True),
    )
    for frame in (splits.train, splits.validation, splits.test):
        assert frame["date"].is_monotonic_increasing
        assert frame.groupby("date").size().eq(2).all()


def test_split_uses_distinct_dates_not_number_of_rows(chronological_data: pd.DataFrame) -> None:
    repeated = pd.concat([chronological_data, chronological_data.iloc[[0]]] * 3, ignore_index=True)
    config = make_split_config(repeated, DIGEST)
    assert config.train.end == "2015-01-06"
    assert config.validation.end == "2015-01-08"
    assert config.test.start == "2015-01-09"


def test_boundaries_ignore_targets_and_input_order(chronological_data: pd.DataFrame) -> None:
    expected = make_split_config(chronological_data, DIGEST)
    changed = chronological_data.iloc[::-1].copy()
    changed["actual_productivity"] = 999.0
    assert make_split_config(changed, DIGEST) == expected
    assert make_split_config(chronological_data[["date"]], DIGEST) == expected


@pytest.mark.parametrize("n_dates", [0, 1, 2])
def test_insufficient_dates_fail(chronological_data: pd.DataFrame, n_dates: int) -> None:
    with pytest.raises(ValueError, match="three distinct dates"):
        make_split_config(chronological_data.iloc[: 2 * n_dates], DIGEST)


def test_three_dates_produce_three_nonempty_partitions(chronological_data: pd.DataFrame) -> None:
    config = make_split_config(chronological_data.iloc[:6], DIGEST)
    assert [
        config.train.distinct_dates,
        config.validation.distinct_dates,
        config.test.distinct_dates,
    ] == [1, 1, 1]


@pytest.mark.parametrize("kind", ["text", "missing", "time", "timezone"])
def test_dates_must_be_parsed_complete_calendar_dates(
    chronological_data: pd.DataFrame, kind: str
) -> None:
    if kind == "text":
        chronological_data["date"] = chronological_data["date"].astype("string")
    elif kind == "missing":
        chronological_data.loc[0, "date"] = pd.NaT
    elif kind == "time":
        chronological_data.loc[0, "date"] += pd.Timedelta(hours=1)
    else:
        chronological_data["date"] = chronological_data["date"].dt.tz_localize("UTC")
    with pytest.raises(ValueError, match="dates"):
        make_split_config(chronological_data, DIGEST)


@pytest.mark.parametrize("change", ["overlap", "count", "policy", "version", "fingerprint"])
def test_config_drift_is_rejected(chronological_data: pd.DataFrame, change: str) -> None:
    config = make_split_config(chronological_data, DIGEST)
    if change == "overlap":
        config = replace(config, validation=replace(config.validation, start=config.train.end))
    elif change == "count":
        config = replace(config, test=replace(config.test, rows=999))
    elif change == "policy":
        config = replace(config, strategy="random-row-split")
    elif change == "version":
        config = replace(config, schema_version=2)
    else:
        config = replace(config, dataset_sha256="b" * 64)
    with pytest.raises(ValueError):
        apply_split_config(chronological_data, config, dataset_sha256=DIGEST)


def test_saved_config_round_trips_and_cannot_be_overwritten(
    chronological_data: pd.DataFrame, tmp_path: Path
) -> None:
    config = make_split_config(chronological_data, DIGEST)
    path = tmp_path / "split.json"
    save_split_config(config, path)
    original = path.read_bytes()
    assert load_split_config(path) == config
    with pytest.raises(FileExistsError):
        save_split_config(config, path)
    assert path.read_bytes() == original


@pytest.mark.parametrize("content", ["not json", "{}", "[]", "null"])
def test_malformed_config_has_clear_error(tmp_path: Path, content: str) -> None:
    path = tmp_path / "invalid.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid split configuration"):
        load_split_config(path)


def test_split_cli_reuses_validation_and_keeps_source_unchanged(
    chronological_csv: Path, tmp_path: Path
) -> None:
    original = chronological_csv.read_bytes()
    output = tmp_path / "config.json"
    assert main(["--dataset", str(chronological_csv), "--output", str(output)]) == 0
    config = load_split_config(output)
    assert config.dataset_sha256 == fingerprint(chronological_csv)
    data, result = load_validated_csv(chronological_csv)
    assert result.passed
    assert len(data) == 20
    assert main(["--dataset", str(chronological_csv), "--output", str(output)]) == 2
    assert chronological_csv.read_bytes() == original


def test_split_cli_rejects_invalid_data(chronological_csv: Path, tmp_path: Path) -> None:
    text = chronological_csv.read_text(encoding="utf-8").replace("Quarter1", "Quarter6")
    chronological_csv.write_text(text, encoding="utf-8")
    output = tmp_path / "config.json"
    assert main(["--dataset", str(chronological_csv), "--output", str(output)]) == 2
    assert not output.exists()
