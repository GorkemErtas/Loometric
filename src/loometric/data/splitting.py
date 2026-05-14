"""Frozen chronological partitions chosen from dates, never target values."""

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from loometric.data.loading import load_validated_csv
from loometric.data.profiling import fingerprint

DEFAULT_CONFIG = Path("configs/chronological_split.json")
STRATEGY = "distinct-date-floor-60-20-20-v1"
PARTITIONS = ("train", "validation", "test")


@dataclass(frozen=True)
class DateRange:
    start: str
    end: str
    distinct_dates: int
    rows: int


@dataclass(frozen=True)
class SplitConfig:
    dataset_sha256: str
    train: DateRange
    validation: DateRange
    test: DateRange
    schema_version: int = 1
    strategy: str = STRATEGY


@dataclass(frozen=True)
class DataSplits:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame


def make_split_config(data: pd.DataFrame, dataset_sha256: str) -> SplitConfig:
    """Use floor(3*n/5) and floor(4*n/5) boundaries, counting distinct dates."""
    if not re.fullmatch(r"[0-9a-f]{64}", dataset_sha256):
        raise ValueError("Dataset fingerprint must be a lowercase SHA-256 hex digest.")
    if "date" not in data or not pd.api.types.is_datetime64_any_dtype(data["date"]):
        raise ValueError("Split input requires explicitly parsed datetime dates.")
    dates = data["date"]
    if dates.isna().any() or dates.dt.tz is not None or not dates.eq(dates.dt.normalize()).all():
        raise ValueError("Split dates must be complete, timezone-naive calendar dates.")
    unique_dates = dates.drop_duplicates().sort_values().reset_index(drop=True)
    n_dates = len(unique_dates)
    if n_dates < 3:
        raise ValueError("At least three distinct dates are required for nonempty partitions.")
    first, second = 3 * n_dates // 5, 4 * n_dates // 5
    blocks = (
        unique_dates.iloc[:first],
        unique_dates.iloc[first:second],
        unique_dates.iloc[second:],
    )
    ranges = tuple(
        DateRange(
            start=str(block.iloc[0].date()),
            end=str(block.iloc[-1].date()),
            distinct_dates=len(block),
            rows=int(dates.isin(block).sum()),
        )
        for block in blocks
    )
    return SplitConfig(dataset_sha256, *ranges)


def apply_split_config(
    data: pd.DataFrame, config: SplitConfig, *, dataset_sha256: str
) -> DataSplits:
    """Reject source/config drift, then stably sort a copy and preserve complete dates."""
    if dataset_sha256 != config.dataset_sha256:
        raise ValueError("Dataset fingerprint differs from the frozen split configuration.")
    expected = make_split_config(data, dataset_sha256)
    if config != expected:
        raise ValueError("Split configuration differs from the fixed date policy or source counts.")
    ordered = data.sort_values("date", kind="stable").reset_index(drop=True)
    frames = tuple(
        ordered.loc[ordered["date"].between(bounds.start, bounds.end)].copy()
        for bounds in (config.train, config.validation, config.test)
    )
    train, validation, test = frames
    if not (
        train["date"].max() < validation["date"].min()
        and validation["date"].max() < test["date"].min()
    ):
        raise ValueError("Chronological partitions overlap.")
    if sum(len(frame) for frame in frames) != len(data):
        raise ValueError("Every source row must belong to exactly one partition.")
    return DataSplits(train, validation, test)


def save_split_config(config: SplitConfig, path: Path) -> None:
    """Create once; never overwrite frozen partitions as a side effect of rerunning."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as destination:
        destination.write(json.dumps(asdict(config), indent=2, sort_keys=True) + "\n")


def load_split_config(path: Path) -> SplitConfig:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for name in PARTITIONS:
            payload[name] = DateRange(**payload[name])
        return SplitConfig(**payload)
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError(f"Invalid split configuration: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create the frozen date-only split configuration.")
    parser.add_argument(
        "--dataset", type=Path, default=Path("data/raw/garments_worker_productivity.csv")
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    try:
        data, _ = load_validated_csv(args.dataset)
        config = make_split_config(data, fingerprint(args.dataset))
        apply_split_config(data, config, dataset_sha256=config.dataset_sha256)
        save_split_config(config, args.output)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Frozen split configuration created: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
