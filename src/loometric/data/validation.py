"""Source validation with explicit errors and reviewable warnings."""

from dataclasses import dataclass
from math import isfinite
from typing import Literal

import pandas as pd

from loometric.data.schema import (
    CATEGORIES,
    COLUMNS,
    INTEGER_COLUMNS,
    NUMERIC_COLUMNS,
    POSITIVE_COLUMNS,
    TARGET,
)


@dataclass(frozen=True)
class ValidationIssue:
    severity: Literal["error", "warning"]
    code: str
    message: str
    count: int = 0


@dataclass(frozen=True)
class ValidationResult:
    issues: tuple[ValidationIssue, ...]

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


def validate_data(raw: pd.DataFrame, clean: pd.DataFrame) -> ValidationResult:
    """Validate the raw and normalized views without dropping rows or imputing values."""
    issues: list[ValidationIssue] = []

    def add(severity: Literal["error", "warning"], code: str, message: str, count: int) -> None:
        if count:
            issues.append(ValidationIssue(severity, code, message, count))

    missing = sorted(set(COLUMNS) - set(raw.columns))
    unexpected = sorted(set(raw.columns) - set(COLUMNS))
    add("error", "missing_columns", f"Missing columns: {', '.join(missing)}.", len(missing))
    add(
        "error",
        "unexpected_columns",
        f"Unexpected columns: {', '.join(unexpected)}.",
        len(unexpected),
    )
    add("error", "empty_dataset", "CSV contains no data rows.", int(raw.empty))
    if missing or unexpected or raw.empty:
        return ValidationResult(tuple(issues))

    for column in COLUMNS:
        text = raw[column].str.strip()
        blank = text.isna() | text.eq("").fillna(False)
        add(
            "warning" if column == "wip" else "error",
            "missing_values",
            f"{column}: missing values (WIP is assessed separately by department)."
            if column == "wip"
            else f"{column}: required values are missing.",
            int(blank.sum()),
        )
        if column == "date" or column in NUMERIC_COLUMNS:
            bad = ~blank & clean[column].isna()
            add("error", "invalid_values", f"{column}: values cannot be parsed.", int(bad.sum()))

    for column in NUMERIC_COLUMNS:
        values = clean[column].dropna()
        finite = values.map(isfinite)
        add(
            "error", "nonfinite_values", f"{column}: infinite numeric values.", int((~finite).sum())
        )
        add(
            "error",
            "negative_values",
            f"{column}: values must be nonnegative.",
            int(values.lt(0).sum()),
        )
        if column in POSITIVE_COLUMNS:
            add(
                "error",
                "nonpositive_values",
                f"{column}: values must be positive.",
                int(values.eq(0).sum()),
            )
        if column in INTEGER_COLUMNS:
            finite_values = values[finite]
            add(
                "error",
                "fractional_counts",
                f"{column}: values must be whole numbers.",
                int(finite_values.mod(1).ne(0).sum()),
            )

    for column, allowed in CATEGORIES.items():
        unknown = clean[column].notna() & ~clean[column].isin(allowed)
        add("error", "unknown_category", f"{column}: unrecognized category.", int(unknown.sum()))

    target = clean[TARGET].dropna()
    add(
        "error",
        "constant_target",
        "Target has fewer than two distinct observed values.",
        int(target.nunique() < 2),
    )
    # Productivity is a ratio: >1 can represent overachievement, not necessarily invalid data.
    add(
        "warning",
        "target_above_one",
        "Target above 1 requires domain review; retained as-is.",
        int(target.gt(1).sum()),
    )
    add(
        "error",
        "planned_target_above_one",
        "targeted_productivity must be in [0, 1].",
        int(clean["targeted_productivity"].gt(1).sum()),
    )

    dates = clean["date"].dropna()
    add(
        "warning",
        "nonchronological_rows",
        "Source rows are not ordered by increasing date.",
        int(dates.diff().lt(pd.Timedelta(0)).sum()),
    )
    mismatch = clean["date"].notna() & clean["day"].ne(clean["date"].dt.day_name()).fillna(False)
    add(
        "error",
        "weekday_mismatch",
        "day disagrees with the explicitly parsed calendar date.",
        int(mismatch.sum()),
    )
    add(
        "warning",
        "duplicate_rows",
        "Exact normalized duplicate rows; no rows were removed.",
        int(clean.duplicated().sum()),
    )
    keys = clean[["date", "department", "team"]]
    complete_keys = keys.dropna()
    add(
        "warning",
        "duplicate_shift_keys",
        "Repeated (date, department, team); source has no shift ID, so verify the row grain.",
        int(complete_keys.duplicated().sum()),
    )
    add(
        "warning",
        "single_date",
        "Only one observed date; chronological evaluation is impossible.",
        int(dates.nunique() == 1),
    )
    return ValidationResult(tuple(issues))
