import pandas as pd
import pytest

from loometric.data.loading import clean_data
from loometric.data.validation import ValidationResult, validate_data


def _validate(raw: pd.DataFrame) -> ValidationResult:
    return validate_data(raw, clean_data(raw))


def test_expected_wip_blanks_and_overachievement_are_warnings(raw_data: pd.DataFrame) -> None:
    result = _validate(raw_data)
    assert result.passed
    warnings = {issue.code: issue.count for issue in result.issues}
    assert warnings == {"missing_values": 2, "target_above_one": 1}


@pytest.mark.parametrize(
    ("column", "value", "code"),
    [
        ("date", "31/01/2015", "invalid_values"),
        ("actual_productivity", "", "missing_values"),
        ("smv", "not-a-number", "invalid_values"),
        ("wip", "unknown", "invalid_values"),
        ("smv", "inf", "nonfinite_values"),
        ("actual_productivity", "-inf", "nonfinite_values"),
        ("actual_productivity", "-0.1", "negative_values"),
        ("over_time", "-1", "negative_values"),
        ("no_of_workers", "0", "nonpositive_values"),
        ("smv", "0", "nonpositive_values"),
        ("team", "0", "nonpositive_values"),
        ("idle_men", "1.5", "fractional_counts"),
        ("team", "1.5", "fractional_counts"),
        ("quarter", "Quarter6", "unknown_category"),
        ("department", "packing", "unknown_category"),
        ("day", "Thurs", "unknown_category"),
        ("day", "Monday", "weekday_mismatch"),
        ("targeted_productivity", "1.1", "planned_target_above_one"),
    ],
)
def test_invalid_cells_fail_with_diagnostic(
    raw_data: pd.DataFrame, column: str, value: str, code: str
) -> None:
    raw_data.loc[0, column] = value
    result = _validate(raw_data)
    assert not result.passed
    assert any(issue.code == code and issue.severity == "error" for issue in result.issues)


def test_constant_target_fails(raw_data: pd.DataFrame) -> None:
    raw_data["actual_productivity"] = "0.8"
    result = _validate(raw_data)
    assert not result.passed
    assert any(issue.code == "constant_target" for issue in result.issues)


def test_schema_errors_are_reported_without_downstream_crash(raw_data: pd.DataFrame) -> None:
    raw_data = raw_data.drop(columns="wip").assign(unexpected="value")
    result = _validate(raw_data)
    assert not result.passed
    assert {issue.code for issue in result.issues} == {"missing_columns", "unexpected_columns"}


def test_header_only_file_fails(raw_data: pd.DataFrame) -> None:
    result = _validate(raw_data.iloc[:0])
    assert not result.passed
    assert any(issue.code == "empty_dataset" for issue in result.issues)


def test_chronology_checks_preserve_source_order(raw_data: pd.DataFrame) -> None:
    raw_data = raw_data.iloc[::-1].reset_index(drop=True)
    result = _validate(raw_data)
    assert result.passed
    assert any(issue.code == "nonchronological_rows" for issue in result.issues)
    assert clean_data(raw_data)["date"].iloc[0] == pd.Timestamp("2015-01-02")


def test_duplicate_rows_and_shift_keys_are_separately_flagged(raw_data: pd.DataFrame) -> None:
    raw_data = pd.concat([raw_data, raw_data.iloc[[0]]], ignore_index=True)
    result = _validate(raw_data)
    counts = {issue.code: issue.count for issue in result.issues}
    assert counts["duplicate_rows"] == 1
    assert counts["duplicate_shift_keys"] == 1


def test_repeated_shift_key_with_distinct_values_is_flagged(raw_data: pd.DataFrame) -> None:
    extra = raw_data.iloc[[0]].copy()
    extra["actual_productivity"] = "0.9"
    result = _validate(pd.concat([raw_data, extra], ignore_index=True))
    assert any(issue.code == "duplicate_shift_keys" for issue in result.issues)
    assert not any(issue.code == "duplicate_rows" for issue in result.issues)


def test_single_date_warns_about_evaluation(raw_data: pd.DataFrame) -> None:
    result = _validate(raw_data.iloc[:2])
    assert any(issue.code == "single_date" for issue in result.issues)
