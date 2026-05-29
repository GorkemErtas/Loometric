"""Complete-date expanding windows restricted to an already verified training block."""

from dataclasses import dataclass

import pandas as pd

from loometric.data.splitting import DateRange


@dataclass(frozen=True)
class ExpandingWindowPolicy:
    min_training_dates: int = 15
    evaluation_dates: int = 5


DEFAULT_POLICY = ExpandingWindowPolicy()


@dataclass(frozen=True)
class TemporalFold:
    name: str
    train: DateRange
    evaluation: DateRange


def make_expanding_folds(
    training: pd.DataFrame,
    training_bounds: DateRange,
    policy: ExpandingWindowPolicy = DEFAULT_POLICY,
) -> tuple[TemporalFold, ...]:
    """Use a growing date prefix and disjoint later windows; include a partial tail.

    Input must match the verified original training partition, not the entire CSV.
    Date selection never reads outcomes. Descriptors preserve complete date groups;
    callers slice by their inclusive dates without changing the original split.
    """
    if any(
        type(value) is not int or value <= 0
        for value in (policy.min_training_dates, policy.evaluation_dates)
    ):
        raise ValueError("Window sizes must be positive integers counting observed dates.")
    if "date" not in training or not pd.api.types.is_datetime64_any_dtype(training["date"]):
        raise ValueError("Temporal input requires explicitly parsed calendar dates.")
    dates = training["date"]
    if (
        dates.empty
        or dates.isna().any()
        or dates.dt.tz is not None
        or not dates.eq(dates.dt.normalize()).all()
        or not training.index.is_unique
    ):
        raise ValueError("Temporal input requires complete calendar dates and unique row indices.")
    unique_dates = dates.drop_duplicates().sort_values().reset_index(drop=True)

    def describe(block: pd.Series) -> DateRange:
        return DateRange(
            start=str(block.iloc[0].date()),
            end=str(block.iloc[-1].date()),
            distinct_dates=len(block),
            rows=int(dates.isin(block).sum()),
        )

    if describe(unique_dates) != training_bounds:
        raise ValueError("Temporal input must match the verified original training bounds/counts.")
    if len(unique_dates) <= policy.min_training_dates:
        raise ValueError("At least one evaluation date is required after the training prefix.")
    return tuple(
        TemporalFold(
            name=f"F{number:02d}",
            train=describe(unique_dates.iloc[:end]),
            evaluation=describe(unique_dates.iloc[end : end + policy.evaluation_dates]),
        )
        for number, end in enumerate(
            range(policy.min_training_dates, len(unique_dates), policy.evaluation_dates), start=1
        )
    )
