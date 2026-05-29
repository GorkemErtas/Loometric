from dataclasses import replace

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from loometric.data.splitting import DateRange, make_split_config
from loometric.data.temporal import DEFAULT_POLICY, ExpandingWindowPolicy, make_expanding_folds


def bounds(data: pd.DataFrame) -> DateRange:
    return DateRange(
        str(data["date"].min().date()),
        str(data["date"].max().date()),
        data["date"].nunique(),
        len(data),
    )


def test_default_policy_is_fixed_before_model_evaluation() -> None:
    assert DEFAULT_POLICY == ExpandingWindowPolicy(min_training_dates=15, evaluation_dates=5)


def test_complete_dates_expanding_prefixes_and_nonoverlapping_evaluation(
    chronological_data: pd.DataFrame,
) -> None:
    data = pd.concat([chronological_data, chronological_data.iloc[[8, 8]]], ignore_index=True)
    original = data.copy(deep=True)
    folds = make_expanding_folds(data, bounds(data), ExpandingWindowPolicy(3, 2))
    assert [fold.train.distinct_dates for fold in folds] == [3, 5, 7, 9]
    assert [fold.evaluation.distinct_dates for fold in folds] == [2, 2, 2, 1]
    previous_training: set[int] = set()
    evaluated: set[int] = set()
    for fold in folds:
        train = data.loc[data["date"].between(fold.train.start, fold.train.end)]
        evaluation = data.loc[data["date"].between(fold.evaluation.start, fold.evaluation.end)]
        assert train["date"].max() < evaluation["date"].min()
        assert previous_training.issubset(set(train.index))
        assert evaluated.isdisjoint(set(evaluation.index))
        assert len(train) == fold.train.rows and len(evaluation) == fold.evaluation.rows
        for frame in (train, evaluation):
            for date in frame["date"].unique():
                assert set(frame.index[frame["date"].eq(date)]) == set(
                    data.index[data["date"].eq(date)]
                )
        previous_training = set(train.index)
        evaluated.update(evaluation.index)
    assert evaluated == set(data.index[data["date"].ge("2015-01-04")])
    assert_frame_equal(data, original)


def test_windows_ignore_labels_columns_and_input_order(chronological_data: pd.DataFrame) -> None:
    policy = ExpandingWindowPolicy(3, 2)
    expected = make_expanding_folds(chronological_data, bounds(chronological_data), policy)
    dates_only = chronological_data[["date"]].iloc[::-1].copy()
    assert make_expanding_folds(dates_only, bounds(chronological_data), policy) == expected
    changed = chronological_data.copy(deep=True)
    changed["actual_productivity"] = float("nan")
    assert make_expanding_folds(changed, bounds(chronological_data), policy) == expected


def test_temporal_generator_rejects_full_source_instead_of_training_partition(
    chronological_data: pd.DataFrame,
) -> None:
    config = make_split_config(chronological_data, "a" * 64)
    with pytest.raises(ValueError, match="original training"):
        make_expanding_folds(chronological_data, config.train, ExpandingWindowPolicy(3, 2))


@pytest.mark.parametrize("field", ["start", "rows", "distinct_dates"])
def test_input_must_match_training_metadata(chronological_data: pd.DataFrame, field: str) -> None:
    original = bounds(chronological_data)
    altered = replace(original, **{field: "2014-12-31" if field == "start" else 999})
    with pytest.raises(ValueError, match="bounds/counts"):
        make_expanding_folds(chronological_data, altered, ExpandingWindowPolicy(3, 2))


@pytest.mark.parametrize(
    "policy",
    [
        ExpandingWindowPolicy(0, 2),
        ExpandingWindowPolicy(-1, 2),
        ExpandingWindowPolicy(3, 0),
        ExpandingWindowPolicy(True, 2),
        ExpandingWindowPolicy(3, 1.5),
    ],
)
def test_invalid_policy_fails(
    chronological_data: pd.DataFrame, policy: ExpandingWindowPolicy
) -> None:
    with pytest.raises(ValueError, match="positive integers"):
        make_expanding_folds(chronological_data, bounds(chronological_data), policy)


def test_insufficient_history_fails_without_fabricating_folds(
    chronological_data: pd.DataFrame,
) -> None:
    with pytest.raises(ValueError, match="evaluation date"):
        make_expanding_folds(chronological_data, bounds(chronological_data))


@pytest.mark.parametrize(
    "kind", ["text", "missing", "time", "timezone", "duplicate_index", "empty"]
)
def test_invalid_date_or_row_identity_is_rejected(
    chronological_data: pd.DataFrame, kind: str
) -> None:
    metadata = bounds(chronological_data)
    data = chronological_data.copy(deep=True)
    if kind == "text":
        data["date"] = data["date"].astype(str)
    elif kind == "missing":
        data.loc[0, "date"] = pd.NaT
    elif kind == "time":
        data.loc[0, "date"] += pd.Timedelta(hours=1)
    elif kind == "timezone":
        data["date"] = data["date"].dt.tz_localize("UTC")
    elif kind == "duplicate_index":
        data.index = [0] * len(data)
    else:
        data = data.iloc[:0]
    with pytest.raises(ValueError, match="calendar dates|row indices"):
        make_expanding_folds(data, metadata, ExpandingWindowPolicy(3, 2))
