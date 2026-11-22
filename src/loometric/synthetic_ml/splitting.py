"""Date/entity assignments depend on declared design only, never target values."""

from datetime import date, timedelta

from loometric.synthetic_ml.configuration import GenerationConfig

TEST_POPULATIONS = (
    "future_familiar",
    "unseen_crew",
    "unseen_line",
    "unseen_factory",
    "unseen_style",
)


def date_partitions(config: GenerationConfig) -> dict[date, str]:
    days = [config.start_date + timedelta(days=i) for i in range(config.calendar_days)]
    days = [day for day in days if day.weekday() != 6]  # Explicit synthetic Mon–Sat calendar.
    a, b, gap = 3 * len(days) // 5, 4 * len(days) // 5, config.embargo_dates
    if a - gap < 8 or b - a - gap < 2 or len(days) - b < 6:
        raise ValueError(
            "Calendar cannot support declared training/validation/five test populations."
        )
    return {
        day: "train"
        if i < a - gap
        else "gap"
        if i < a
        else "validation"
        if i < b - gap
        else "gap"
        if i < b
        else "test"
        for i, day in enumerate(days)
    }


def population(factory: str, line: str, crew: str, style: str, config: GenerationConfig) -> str:
    if factory == f"F{config.factories - 1:02}":
        return "unseen_factory"
    if line.endswith(f"-{config.lines_per_stage - 1:02}"):
        return "unseen_line"
    if crew.endswith("-H"):
        return "unseen_crew"
    if style == f"S{config.styles - 1:02}":
        return "unseen_style"
    return "future_familiar"
