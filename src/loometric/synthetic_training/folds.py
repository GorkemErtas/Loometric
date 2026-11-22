"""Expanding original-training windows, purged dates and strict label maturity."""

from dataclasses import dataclass

from loometric.synthetic_training.data import Population, require


@dataclass(frozen=True)
class Fold:
    name: str
    train_ids: tuple[str, ...]
    evaluation_ids: tuple[str, ...]
    train_dates: tuple[str, ...]
    evaluation_dates: tuple[str, ...]


def expanding_folds(training: Population) -> tuple[Fold, ...]:
    dates = sorted(set(training.metadata.start_date))
    n, width = len(dates), len(dates) // 6
    require(n >= 18 and width >= 2, "INSUFFICIENT_TRAINING_DATES_FOR_FROZEN_FOLDS")
    result, seen = [], set()
    for i, start in enumerate((n // 2, 2 * n // 3, 5 * n // 6), 1):
        train_dates = dates[: start - 1]
        evaluation_dates = dates[start : start + width]
        tr = tuple(training.X.index[training.metadata.start_date.isin(train_dates)])
        ev = tuple(training.X.index[training.metadata.start_date.isin(evaluation_dates)])
        require(
            bool(tr) and bool(ev) and not seen.intersection(ev) and not set(tr).intersection(ev),
            "FOLD_POPULATION_OVERLAP_OR_EMPTY",
        )
        require(
            max(training.metadata.loc[list(tr), "label_available_at"])
            < min(training.metadata.loc[list(ev), "cutoff"]),
            "FOLD_LABEL_MATURITY_FAILURE",
        )
        seen.update(ev)
        result.append(
            Fold(
                f"F{i:02}",
                tr,
                ev,
                tuple(d.isoformat() for d in train_dates),
                tuple(d.isoformat() for d in evaluation_dates),
            )
        )
    return tuple(result)
