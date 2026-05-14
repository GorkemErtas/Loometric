"""Read source text without inferring dates or silently changing raw files."""

import csv
from pathlib import Path

import pandas as pd

from loometric.data.schema import DATE_FORMAT, NUMERIC_COLUMNS
from loometric.data.validation import ValidationResult, validate_data


class DatasetReadError(ValueError):
    """The CSV cannot be read without losing its structure."""


def read_csv(path: Path) -> pd.DataFrame:
    """Read all cells as strings; reject duplicate headers and ragged records."""
    try:
        with path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.reader(source, strict=True)
            header = next(reader, None)
            if not header or any(not name.strip() for name in header):
                raise DatasetReadError("CSV must have a nonempty header with named columns.")
            if len(header) != len(set(header)):
                raise DatasetReadError("CSV contains duplicate column names.")
            records: list[list[str]] = []
            for record in reader:
                if len(record) != len(header):
                    raise DatasetReadError(
                        f"CSV record ending at line {reader.line_num} has {len(record)} cells; "
                        f"expected {len(header)}."
                    )
                records.append(record)
    except (csv.Error, UnicodeError) as exc:
        raise DatasetReadError(f"Cannot parse CSV: {exc}") from exc
    return pd.DataFrame(records, columns=header, dtype="string")


def clean_data(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize a copy. Invalid values become missing and are checked against raw data."""
    clean = raw.copy(deep=True)
    for column in clean.columns:
        clean[column] = clean[column].str.strip().replace("", pd.NA)
    if "date" in clean:
        clean["date"] = pd.to_datetime(clean["date"], format=DATE_FORMAT, errors="coerce")
    if "department" in clean:
        clean["department"] = clean["department"].str.lower().replace({"sweing": "sewing"})
    for column in NUMERIC_COLUMNS:
        if column in clean:
            clean[column] = pd.to_numeric(clean[column], errors="coerce").astype("Float64")
    return clean


def load_validated_csv(path: Path) -> tuple[pd.DataFrame, ValidationResult]:
    """Reuse source checks before experiments; leave normalization and EDA behavior intact."""
    raw = read_csv(path)
    clean = clean_data(raw)
    result = validate_data(raw, clean)
    if not result.passed:
        errors = "; ".join(issue.message for issue in result.issues if issue.severity == "error")
        raise ValueError(f"Dataset validation failed: {errors}")
    return clean, result
