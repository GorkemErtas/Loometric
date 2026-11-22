"""Closed configuration, bounded sizes and synthetic assumptions only."""

from dataclasses import dataclass, fields
from datetime import date, timedelta
from pathlib import Path

from loometric.planning.loading import parse_date, parse_json


@dataclass(frozen=True)
class GenerationConfig:
    seed: int = 42
    scenario: str = "baseline"
    start_date: date = date(2030, 1, 7)
    calendar_days: int = 56
    factories: int = 3
    lines_per_stage: int = 2
    styles: int = 6
    workers_min: int = 4
    workers_max: int = 16
    standard_hundredths_min: int = 50
    standard_hundredths_max: int = 1500
    workload_percent_min: int = 35
    workload_percent_max: int = 160
    planned_downtime_max: int = 60
    process_noise_bps: int = 1800
    difficult_per_thousand: int = 25
    label_delay_minutes: int = 120
    embargo_dates: int = 1

    def __post_init__(self) -> None:
        bounds = {
            "seed": (0, 2**32 - 1),
            "calendar_days": (35, 730),
            "factories": (2, 8),
            "lines_per_stage": (2, 4),
            "styles": (3, 24),
            "workers_min": (1, 100),
            "workers_max": (1, 100),
            "standard_hundredths_min": (1, 10000),
            "standard_hundredths_max": (1, 10000),
            "workload_percent_min": (1, 1000),
            "workload_percent_max": (1, 1000),
            "planned_downtime_max": (0, 120),
            "process_noise_bps": (0, 4000),
            "difficult_per_thousand": (0, 1000),
            "label_delay_minutes": (0, 720),
            "embargo_dates": (0, 3),
        }
        for name, (low, high) in bounds.items():
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"Unsupported synthetic configuration range: {name}.")
        if self.scenario not in ("baseline", "disruption", "workload_surge"):
            raise ValueError("Unsupported synthetic distribution-shift scenario.")
        if type(self.start_date) is not date or self.start_date.year < 2020:
            raise ValueError("Use an explicit synthetic calendar date from 2020 onward.")
        if any(
            getattr(self, a) > getattr(self, b)
            for a, b in (
                ("workers_min", "workers_max"),
                ("standard_hundredths_min", "standard_hundredths_max"),
                ("workload_percent_min", "workload_percent_max"),
            )
        ):
            raise ValueError("Synthetic minimum exceeds maximum.")
        self.start_date + timedelta(days=self.calendar_days + 3)
        # Bound work before allocating entities; sizes derive from exposure, not quality targets.
        if self.calendar_days * self.factories * 5 * self.lines_per_stage * 2 > 150000:
            raise ValueError("Synthetic generation exceeds 150,000 candidate line-shifts.")


def load_configuration(path: Path, profile: str, seed: int, scenario: str) -> GenerationConfig:
    if path.stat().st_size > 32768:
        raise ValueError("Synthetic configuration exceeds 32 KiB.")
    data = parse_json(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {
        "schema_version",
        "dataset_version",
        "seeds",
        "scenarios",
        "profiles",
    }:
        raise ValueError("Closed synthetic generation configuration required.")
    if (
        type(data["schema_version"]) is not int
        or data["schema_version"] != 1
        or data["dataset_version"] != "synthetic-ml-v1"
    ):
        raise ValueError("Unsupported synthetic dataset configuration version.")
    if (
        not isinstance(data["seeds"], list)
        or not data["seeds"]
        or any(type(s) is not int or not 0 <= s < 2**32 for s in data["seeds"])
        or len(set(data["seeds"])) != len(data["seeds"])
        or not isinstance(data["scenarios"], list)
        or not data["scenarios"]
        or any(s not in ("baseline", "disruption", "workload_surge") for s in data["scenarios"])
        or len(set(data["scenarios"])) != len(data["scenarios"])
        or not isinstance(data["profiles"], dict)
        or not data["profiles"]
    ):
        raise ValueError("Explicit unique seed/scenario lists and named profiles are required.")
    if type(seed) is not int or seed not in data["seeds"] or scenario not in data["scenarios"]:
        raise ValueError("Seed/scenario must be declared in the generation configuration.")
    raw = data["profiles"][profile]
    if not isinstance(raw, dict) or set(raw) - {f.name for f in fields(GenerationConfig)}:
        raise ValueError("Unsupported generation profile fields.")
    if {"seed", "scenario"} & set(raw):
        raise ValueError("Seed/scenario selection is explicit, outside the size profile.")
    raw = dict(raw)
    if "start_date" in raw:
        raw["start_date"] = parse_date(raw["start_date"])
    return GenerationConfig(**raw, seed=seed, scenario=scenario)
