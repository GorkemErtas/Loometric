from pathlib import Path

import pandas as pd
import pytest

from loometric.cli import main
from loometric.data.loading import clean_data, read_csv
from loometric.data.profiling import build_profile, fingerprint
from loometric.data.schema import COLUMNS
from loometric.data.validation import validate_data
from loometric.leakage import FEATURE_POLICIES


def test_report_profiles_department_missingness_and_target(raw_data: pd.DataFrame) -> None:
    clean = clean_data(raw_data)
    report = build_profile(
        raw_data,
        clean,
        validate_data(raw_data, clean),
        source=Path("synthetic.csv"),
        source_sha256="synthetic-fixture-not-production",
    )
    assert "| finishing | 2 | 2 | 100.00% | 0 | N/A | N/A | N/A |" in report
    assert "| sewing | 2 | 0 | 0.00% | 0 | 90 | 95 | 100 |" in report
    assert "| > 1.00 (review) | 1 | 25.00% |" in report
    assert "| 2015-01-01 | 2 | 0.775 | 0.775 |" in report
    assert "pre_shift" in report and "post_shift" in report
    assert "retrospective associations" in report.lower()
    assert "Quarter5" in report


def test_each_source_field_has_one_availability_policy() -> None:
    policies = {policy.name: policy.availability for policy in FEATURE_POLICIES}
    assert len(policies) == len(FEATURE_POLICIES) == len(COLUMNS)
    assert set(policies) == set(COLUMNS)
    for name in ("over_time", "incentive", "idle_time", "idle_men"):
        assert policies[name] == "post_shift"
    for name in ("wip", "no_of_workers", "no_of_style_change", "targeted_productivity", "smv"):
        assert policies[name] == "conditional"
    assert policies["actual_productivity"] == "target"


def test_cli_report_is_reproducible_and_raw_is_unchanged(
    dataset_path: Path, tmp_path: Path
) -> None:
    output = tmp_path / "docs" / "profile.md"
    args = ["--dataset", str(dataset_path), "--output", str(output)]
    original = dataset_path.read_bytes()
    assert main(args) == 0
    report = output.read_bytes()
    assert fingerprint(dataset_path) in report.decode("utf-8")
    assert main(args) == 0
    assert output.read_bytes() == report
    assert dataset_path.read_bytes() == original
    assert str(tmp_path) not in report.decode("utf-8")


def test_missing_dataset_does_not_overwrite_existing_report(tmp_path: Path) -> None:
    output = tmp_path / "profile.md"
    output.write_text("existing report", encoding="utf-8")
    assert main(["--dataset", str(tmp_path / "absent.csv"), "--output", str(output)]) == 2
    assert output.read_text(encoding="utf-8") == "existing report"


def test_cli_cannot_overwrite_source(dataset_path: Path) -> None:
    original = dataset_path.read_bytes()
    assert main(["--dataset", str(dataset_path), "--output", str(dataset_path)]) == 2
    assert dataset_path.read_bytes() == original


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("actual_productivity", ""),
        ("actual_productivity", "inf"),
        ("actual_productivity", "-0.1"),
        ("department", ""),
        ("date", "invalid"),
        ("wip", "bad"),
        ("smv", "inf"),
    ],
)
def test_invalid_dataset_still_writes_actionable_report(
    dataset_path: Path, tmp_path: Path, column: str, value: str
) -> None:
    raw = read_csv(dataset_path)
    raw.loc[0, column] = value
    raw.to_csv(dataset_path, index=False)
    output = tmp_path / "invalid-profile.md"
    assert main(["--dataset", str(dataset_path), "--output", str(output)]) == 1
    assert "validation: **FAIL**" in output.read_text(encoding="utf-8")


def test_invalid_schema_writes_validation_without_inventing_eda(
    dataset_path: Path, tmp_path: Path
) -> None:
    raw = read_csv(dataset_path).drop(columns="wip")
    raw.to_csv(dataset_path, index=False)
    output = tmp_path / "invalid-schema.md"
    assert main(["--dataset", str(dataset_path), "--output", str(output)]) == 1
    report = output.read_text(encoding="utf-8")
    assert "Missing columns: wip" in report
    assert "No dataset statistics have been invented" in report


def test_no_observed_target_does_not_crash_report(dataset_path: Path, tmp_path: Path) -> None:
    raw = read_csv(dataset_path)
    raw["actual_productivity"] = ""
    raw.to_csv(dataset_path, index=False)
    output = tmp_path / "missing-target.md"
    assert main(["--dataset", str(dataset_path), "--output", str(output)]) == 1
    assert "No finite target observations" in output.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("column", "expected_exit"),
    [
        ("date", 1),
        ("department", 1),
        ("team", 1),
        ("wip", 0),
    ],
)
def test_entirely_missing_column_still_produces_report(
    dataset_path: Path, tmp_path: Path, column: str, expected_exit: int
) -> None:
    raw = read_csv(dataset_path)
    raw[column] = ""
    raw.to_csv(dataset_path, index=False)
    output = tmp_path / "all-missing-column.md"
    assert main(["--dataset", str(dataset_path), "--output", str(output)]) == expected_exit
    assert "missing_values" in output.read_text(encoding="utf-8")


def test_malformed_csv_does_not_replace_existing_report(tmp_path: Path) -> None:
    dataset = tmp_path / "malformed.csv"
    dataset.write_text("a,a\n1,2\n", encoding="utf-8")
    output = tmp_path / "profile.md"
    output.write_text("existing report", encoding="utf-8")
    assert main(["--dataset", str(dataset), "--output", str(output)]) == 2
    assert output.read_text(encoding="utf-8") == "existing report"


def test_output_error_returns_io_exit_code(
    dataset_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    parent = tmp_path / "file-instead-of-directory"
    parent.write_text("keep this file", encoding="utf-8")
    output = parent / "profile.md"
    assert main(["--dataset", str(dataset_path), "--output", str(output)]) == 2
    assert "cannot write profile" in capsys.readouterr().err
    assert parent.read_text(encoding="utf-8") == "keep this file"
