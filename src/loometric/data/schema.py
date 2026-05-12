"""The expected source contract, kept separate from ingestion and reporting."""

DATE_FORMAT = "%m/%d/%Y"
TARGET = "actual_productivity"

COLUMNS = (
    "date",
    "quarter",
    "department",
    "day",
    "team",
    "targeted_productivity",
    "smv",
    "wip",
    "over_time",
    "incentive",
    "idle_time",
    "idle_men",
    "no_of_style_change",
    "no_of_workers",
    TARGET,
)

NUMERIC_COLUMNS = COLUMNS[4:]
INTEGER_COLUMNS = ("team", "wip", "over_time", "incentive", "idle_men", "no_of_style_change")
POSITIVE_COLUMNS = ("team", "smv", "no_of_workers")
CATEGORIES: dict[str, tuple[str, ...]] = {
    "department": ("sewing", "finishing"),
    "quarter": tuple(f"Quarter{i}" for i in range(1, 6)),
    "day": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
}
