"""Stateless, provisional pre-shift inputs; no outcomes or fitted statistics."""

import pandas as pd

SOURCE_COLUMNS = ("date", "department", "team")
CATEGORICAL_FEATURES = ("department", "team", "day_of_week")
NUMERIC_FEATURES = ("day_of_month",)
# Fixed before observing EXP-002 results. Order breaks numerical MAE ties in favor
# of the simpler set. Ablations measure department, team, and joint calendar effects.
FEATURE_SETS = (
    ("department_only", ("department",)),
    ("team_only", ("team",)),
    ("department_team", ("department", "team")),
    ("department_team_calendar", ("department", "team", "day_of_week", "day_of_month")),
)


def validate_feature_names(columns: tuple[str, ...]) -> None:
    """A closed allowlist prevents conditional, realized, or label inputs."""
    allowed = set(CATEGORICAL_FEATURES + NUMERIC_FEATURES)
    if not columns or len(set(columns)) != len(columns) or set(columns) - allowed:
        raise ValueError("Features must be unique, nonempty, provisionally eligible inputs.")


def build_features(scheduled: pd.DataFrame) -> pd.DataFrame:
    """Require a narrow normalized snapshot; preserve every row and its index.

    Department/team assignments and the scheduled date must exist before the shift.
    Timing is unverified in the source. Numeric team IDs become canonical strings,
    never magnitudes. Weekday is Monday=0 through Sunday=6 (categorical); day of
    month is 1..31 (numeric). The source's day/quarter fields are never consumed.
    """
    if not scheduled.columns.is_unique or set(scheduled.columns) != set(SOURCE_COLUMNS):
        raise ValueError("Feature input must contain only date, department, and team.")
    if scheduled.empty or scheduled.isna().any().any():
        raise ValueError("Scheduled inputs must be nonempty and complete; no imputation.")
    dates = scheduled["date"]
    if not pd.api.types.is_datetime64_any_dtype(dates):
        raise ValueError("Scheduled dates must be explicitly parsed calendar dates.")
    if dates.dt.tz is not None or not dates.eq(dates.dt.normalize()).all():
        raise ValueError("Scheduled dates must be timezone-naive calendar dates.")
    departments = scheduled["department"]
    if not departments.map(lambda value: isinstance(value, str) and bool(value.strip())).all():
        raise ValueError("Scheduled departments must be nonblank strings.")
    try:
        teams = pd.to_numeric(scheduled["team"], errors="raise")
        valid = teams.gt(0) & teams.lt(float("inf")) & teams.mod(1).eq(0)
        if not valid.all():
            raise ValueError("Invalid team IDs.")
        team_ids = teams.map(lambda value: str(int(value)))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Team IDs must be finite, positive whole numbers.") from exc
    return pd.DataFrame(
        {
            "department": departments.copy(),
            "team": team_ids,
            "day_of_week": dates.dt.day_of_week.astype(str),
            "day_of_month": dates.dt.day.astype("float64"),
        },
        index=scheduled.index,
    )
