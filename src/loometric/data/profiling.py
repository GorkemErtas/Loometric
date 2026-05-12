"""Deterministic, descriptive Markdown reporting; no modeling or data fitting."""

from collections.abc import Iterable, Sequence
from hashlib import sha256
from pathlib import Path

import pandas as pd

from loometric.data.schema import CATEGORIES, COLUMNS, NUMERIC_COLUMNS, TARGET
from loometric.data.validation import ValidationResult
from loometric.leakage import leakage_markdown


def _format(value: object) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def _table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(_format(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def _numeric(data: pd.DataFrame, column: str) -> pd.Series:
    return data[column].replace([float("inf"), float("-inf")], pd.NA).dropna()


def _chronology(data: pd.DataFrame) -> str:
    dates = data["date"].dropna()
    if dates.empty:
        return "No valid dates are available."
    counts = dates.value_counts().sort_index()
    gaps = pd.date_range(dates.min(), dates.max()).difference(dates.unique())
    mismatch = data["date"].notna() & data["day"].ne(data["date"].dt.day_name()).fillna(False)
    summary = _table(
        ["Check", "Observed"],
        [
            ["Explicit input format", "MM/DD/YYYY (%m/%d/%Y)"],
            ["First date", dates.min().date()],
            ["Last date", dates.max().date()],
            ["Distinct dates", dates.nunique()],
            ["Missing/invalid dates", len(data) - len(dates)],
            ["Weekday disagreements", int(mismatch.sum())],
            ["Date reversals in source row order", int(dates.diff().lt(pd.Timedelta(0)).sum())],
            ["Unobserved calendar dates within range", len(gaps)],
            ["Exact normalized duplicate rows", int(data.duplicated().sum())],
            [
                "Repeated complete (date, department, team) keys",
                int(data[["date", "department", "team"]].dropna().duplicated().sum()),
            ],
            ["Minimum rows per observed date", counts.min()],
            ["Maximum rows per observed date", counts.max()],
        ],
    )
    gap_description = ", ".join(str(date.date()) for date in gaps) or "none"
    return (
        summary
        + f"\n\nUnobserved calendar dates: {gap_description}."
        + (
            "\n\nDates are not silently sorted. Repeated dates are expected for multiple teams; "
            "all rows on one date must stay together in future chronological evaluation. Missing "
            "calendar dates do not prove missing shifts without a production calendar. The source "
            "contains dates but no shift times, shift IDs, or measurement timestamps."
        )
    )


def _categories(raw: pd.DataFrame, data: pd.DataFrame) -> str:
    sections = [
        "Whitespace is trimmed; department spelling `sweing` is mapped to `sewing`. "
        "Raw files remain unchanged. Category values outside the contract are errors."
    ]
    sections.extend(
        [
            "\nRaw department labels (quotes expose trailing spaces):",
            _table(
                ["Raw label", "Rows"],
                [
                    [repr(label), count]
                    for label, count in raw["department"].value_counts(dropna=False).items()
                ],
            ),
        ]
    )
    for column, allowed in CATEGORIES.items():
        counts = data[column].value_counts(dropna=False)
        unobserved = ", ".join(value for value in allowed if value not in counts) or "none"
        sections.extend(
            [
                f"\n### {column}",
                f"Expected categories: {', '.join(allowed)}.",
                _table(
                    ["Category", "Rows", "Percent of all rows"],
                    [
                        [label, count, f"{100 * count / len(data):.2f}%"]
                        for label, count in counts.sort_index().items()
                    ],
                ),
                f"Unobserved allowed categories: {unobserved}.",
            ]
        )
    team_counts = data["team"].value_counts().sort_index()
    sections.extend(
        [
            "\n### team",
            "Team numbers are identifiers, not an ordinal production measure. "
            "Positive integer IDs are required; no closed team roster is assumed.",
            _table(["Team", "Rows"], list(team_counts.items())),
            "\n`quarter` is a source within-month category, not a financial/calendar quarter. "
            "Its allowed labels are checked; its exact date-bucket semantics need confirmation.",
        ]
    )
    return "\n\n".join(sections)


def _wip(data: pd.DataFrame) -> str:
    rows: list[list[object]] = []
    for department, group in data.groupby("department", dropna=False, sort=True):
        observed = _numeric(group, "wip")
        missing = int(group["wip"].isna().sum())
        rows.append(
            [
                department,
                len(group),
                missing,
                f"{100 * missing / len(group):.2f}%",
                int(observed.eq(0).sum()),
                observed.min(),
                observed.median(),
                observed.max(),
            ]
        )
    return _table(
        [
            "Department",
            "Rows",
            "Missing WIP",
            "Missing %",
            "Observed zeros",
            "Min",
            "Median",
            "Max",
        ],
        rows,
    ) + (
        "\n\nMissing WIP and observed zero WIP are counted separately. The missingness indicator "
        "in this table includes blanks and values that failed numeric parsing; parsing failures "
        "also fail validation. Department association can suggest a structural reporting pattern, "
        "but does not establish why values are absent. Do not fill WIP with zero or a global mean. "
        "First confirm applicability by department and that WIP was recorded before the shift. "
        "Any later imputation must be fit using training dates only."
    )


def _target(data: pd.DataFrame) -> str:
    target = _numeric(data, TARGET)
    if target.empty:
        return "No finite target observations are available; validation must pass before modeling."
    bins = [
        ["< 0 (invalid)", int(target.lt(0).sum())],
        ["0 to < 0.25", int((target.ge(0) & target.lt(0.25)).sum())],
        ["0.25 to < 0.50", int((target.ge(0.25) & target.lt(0.5)).sum())],
        ["0.50 to < 0.75", int((target.ge(0.5) & target.lt(0.75)).sum())],
        ["0.75 to 1.00 (inclusive)", int((target.ge(0.75) & target.le(1)).sum())],
        ["> 1.00 (review)", int(target.gt(1).sum())],
    ]
    summary = _table(
        ["Measure", "Value"],
        [
            ["Finite observations", len(target)],
            ["Missing or invalid observations", len(data) - len(target)],
            ["Unique finite values", target.nunique()],
            ["Mean", target.mean()],
            ["Standard deviation (sample)", target.std() if len(target) > 1 else None],
            ["Skewness", target.skew() if len(target) > 2 else None],
            *[[f"Quantile {q:g}", target.quantile(q)] for q in (0, 0.01, 0.25, 0.5, 0.75, 0.99, 1)],
        ],
    )
    department_rows: list[list[object]] = []
    for department, group in data.groupby("department", dropna=False, sort=True):
        values = _numeric(group, TARGET)
        department_rows.append([department, len(values), values.mean(), values.median()])
    daily = (
        data.assign(_finite_target=data[TARGET].replace([float("inf"), float("-inf")], pd.NA))
        .groupby("date")["_finite_target"]
        .agg(["count", "mean", "median"])
    )
    return "\n\n".join(
        [
            "The target is continuous productivity at the end of the shift. "
            "Negative values, missing/nonfinite observations, or a constant target "
            "fail validation. Values above 1 are retained and flagged for domain review; "
            "they are not silently clipped.",
            summary,
            _table(
                ["Target range", "Rows", "Percent of finite observations"],
                [[label, count, f"{100 * count / len(target):.2f}%"] for label, count in bins],
            ),
            "### Target by department",
            _table(["Department", "Finite targets", "Mean", "Median"], department_rows),
            "### Target by date",
            _table(
                ["Date", "Finite targets", "Mean", "Median"],
                [
                    [date.date(), row["count"], row["mean"], row["median"]]
                    for date, row in daily.iterrows()
                ],
            ),
            "Daily summaries describe observed variation; they do not establish a trend or "
            "prove stability outside the observed period.",
        ]
    )


def _numeric_summary(data: pd.DataFrame) -> str:
    rows: list[list[object]] = []
    for column in NUMERIC_COLUMNS:
        values = _numeric(data, column)
        rows.append(
            [
                column,
                len(values),
                len(data) - len(values),
                values.mean(),
                values.std() if len(values) > 1 else None,
                values.min(),
                values.quantile(0.25),
                values.median(),
                values.quantile(0.75),
                values.max(),
            ]
        )
    return _table(
        [
            "Column",
            "Finite n",
            "Missing/invalid",
            "Mean",
            "Std",
            "Min",
            "P25",
            "Median",
            "P75",
            "Max",
        ],
        rows,
    )


def _associations(data: pd.DataFrame) -> str:
    numeric = data[list(NUMERIC_COLUMNS)].replace([float("inf"), float("-inf")], pd.NA)
    rows: list[list[object]] = []
    for column in NUMERIC_COLUMNS:
        if column in (TARGET, "team"):
            continue
        paired = numeric[[column, TARGET]].dropna()
        enough_variation = len(paired) >= 3 and paired.nunique().min() >= 2
        correlation = paired[column].corr(paired[TARGET]) if enough_variation else None
        rows.append([column, len(paired), correlation])
    return (
        "Pairwise Pearson correlations use finite complete pairs only (at least three pairs "
        "and variation in both fields). Different rows can contribute to each pair. Team IDs "
        "are excluded because they are categorical. These are retrospective associations, "
        "not causal effects, feature recommendations, or evidence of prediction-time availability. "
        "High correlation with an unavailable field cannot justify using it.\n\n"
        + _table(["Column", "Complete pairs", "Correlation with actual_productivity"], rows)
    )


def build_profile(
    raw: pd.DataFrame,
    data: pd.DataFrame,
    validation: ValidationResult,
    *,
    source: Path,
    source_sha256: str,
) -> str:
    """Build a reproducible report with no wall-clock timestamps or absolute host paths."""
    status = "PASS" if validation.passed else "FAIL"
    sections = [
        "# Loometric data profile",
        f"Source: `{source.as_posix()}`  \nSHA-256: `{source_sha256}`  \n"
        f"Rows: **{len(raw)}**; columns: **{len(raw.columns)}**; validation: **{status}**.",
        "This report describes the supplied CSV only. It does not train a model, infer "
        "measurement timing, remove rows, or save a transformed dataset. Numeric summaries "
        "exclude missing, unparseable, and nonfinite values; validation reports those issues.",
        "## Validation",
        _table(
            ["Severity", "Code", "Count", "Finding"],
            [
                [issue.severity, issue.code, issue.count, issue.message]
                for issue in validation.issues
            ],
        )
        if validation.issues
        else "All implemented checks passed with no warnings.",
        "Counts refer to affected values or rows unless the finding describes schema columns. "
        "Duplicate counts count repetitions after the first occurrence. Warnings require review "
        "but do not cause a nonzero exit; errors do.",
    ]
    if not raw.empty and set(COLUMNS) == set(data.columns):
        sections.extend(
            [
                "## Dates and chronology",
                _chronology(data),
                "## Categories",
                _categories(raw, data),
                "## Missing WIP by department",
                _wip(data),
                "## Target distribution",
                _target(data),
                "## Numeric summary",
                _numeric_summary(data),
                "## Retrospective associations",
                _associations(data),
            ]
        )
    else:
        sections.append(
            "Descriptive analysis is unavailable until schema and row-count errors "
            "are resolved. No dataset statistics have been invented."
        )
    sections.extend(
        [
            "## Pre-shift problem and leakage assessment",
            "Predict a scheduled team's department-level `actual_productivity` for one upcoming "
            "shift using information frozen immediately before that shift starts. The tentative "
            "source grain is (date, department, team); repeated keys need source-owner review "
            "because the CSV does not identify individual shifts.",
            leakage_markdown(),
            "## Next data decisions",
            "Confirm row grain, productivity units and values above 1, pre-shift field timestamps, "
            "fractional staffing, within-month quarter semantics, and department WIP reporting. "
            "Resolve validation errors before any training. Choose future date "
            "boundaries based on the available history; no dates or split ratios are guessed here.",
        ]
    )
    return "\n\n".join(sections) + "\n"


def fingerprint(path: Path) -> str:
    """Hash source bytes so regenerated reports can be tied to a specific CSV."""
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
