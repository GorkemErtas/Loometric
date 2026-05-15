from dataclasses import asdict
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

import loometric.experiments.naive as naive
import loometric.experiments.reporting as reporting
from loometric.data.loading import load_validated_csv
from loometric.data.profiling import fingerprint
from loometric.data.schema import TARGET
from loometric.data.splitting import apply_split_config, make_split_config, save_split_config
from loometric.evaluation import RegressionMetrics

DIGEST = "a" * 64


def test_final_test_targets_cannot_affect_fitted_means_or_validation_results(
    chronological_data: pd.DataFrame,
) -> None:
    config = make_split_config(chronological_data, DIGEST)
    expected = naive.run_experiment(chronological_data, config, dataset_sha256=DIGEST)
    changed = chronological_data.copy(deep=True)
    changed.loc[changed["date"].ge(config.test.start), TARGET] = 999999.0
    actual = naive.run_experiment(changed, config, dataset_sha256=DIGEST)
    assert asdict(actual) == asdict(expected)


def test_validation_targets_never_estimate_baseline_means(chronological_data: pd.DataFrame) -> None:
    config = make_split_config(chronological_data, DIGEST)
    expected = naive.run_experiment(chronological_data, config, dataset_sha256=DIGEST)
    changed = chronological_data.copy(deep=True)
    changed.loc[changed["date"].between(config.validation.start, config.validation.end), TARGET] = (
        5.0
    )
    actual = naive.run_experiment(changed, config, dataset_sha256=DIGEST)
    assert actual.global_mean == expected.global_mean
    assert actual.department_means == expected.department_means
    assert actual.validation_metrics != expected.validation_metrics


def test_post_shift_and_unverified_features_never_enter_predictors(
    chronological_data: pd.DataFrame,
) -> None:
    config = make_split_config(chronological_data, DIGEST)
    expected = naive.run_experiment(chronological_data, config, dataset_sha256=DIGEST)
    minimal = chronological_data[["date", "department", TARGET]].copy()
    assert naive.run_experiment(minimal, config, dataset_sha256=DIGEST) == expected


def test_experiment_never_requests_the_test_frame_or_scores_test_rows(
    chronological_data: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = make_split_config(chronological_data, DIGEST)
    splits = apply_split_config(chronological_data, config, dataset_sha256=DIGEST)
    development_only = SimpleNamespace(train=splits.train, validation=splits.validation)
    monkeypatch.setattr(naive, "apply_split_config", lambda *args, **kwargs: development_only)
    observed_counts = []
    real_metrics = naive.regression_metrics

    def score_validation_only(actual: pd.Series, predicted: pd.Series) -> RegressionMetrics:
        assert set(actual.index).issubset(set(splits.validation.index))
        assert set(actual.index).isdisjoint(set(splits.test.index))
        observed_counts.append(len(actual))
        return real_metrics(actual, predicted)

    monkeypatch.setattr(naive, "regression_metrics", score_validation_only)
    result = naive.run_experiment(chronological_data, config, dataset_sha256=DIGEST)
    assert result.validation_metrics["global_mean"].samples == 4
    assert observed_counts == [4, 4, 2, 2, 2, 2]


def test_department_mae_matches_independently_calculated_slice(
    chronological_data: pd.DataFrame,
) -> None:
    config = make_split_config(chronological_data, DIGEST)
    result = naive.run_experiment(chronological_data, config, dataset_sha256=DIGEST)
    # Six training dates have mean date increment 0.05; validation increments are 0.12 and 0.14.
    assert result.global_mean == pytest.approx(0.45)
    assert result.department_means == pytest.approx({"sewing": 0.35, "finishing": 0.55})
    assert result.department_scores["sewing"].department_mae == pytest.approx(0.08)
    assert result.department_scores["finishing"].department_mae == pytest.approx(0.08)
    assert result.department_scores["sewing"].training_samples == 6
    assert result.department_scores["sewing"].validation_samples == 2


def test_experiment_cli_preserves_inputs_and_records_validation_only(
    chronological_csv: Path, tmp_path: Path
) -> None:
    data, _ = load_validated_csv(chronological_csv)
    config = make_split_config(data, fingerprint(chronological_csv))
    config_path = tmp_path / "split.json"
    save_split_config(config, config_path)
    original_source, original_config = chronological_csv.read_bytes(), config_path.read_bytes()
    output = tmp_path / "EXP-001.md"
    arguments = [
        "--dataset",
        str(chronological_csv),
        "--split-config",
        str(config_path),
        "--output",
        str(output),
    ]
    assert naive.main(arguments) == 0
    report = output.read_text(encoding="utf-8")
    assert "| global_mean | 12 | 4 |" in report
    assert "| department_mean | 12 | 4 |" in report
    assert "Reserved; no metrics" in report
    assert config.dataset_sha256 in report
    assert chronological_csv.read_bytes() == original_source
    assert config_path.read_bytes() == original_config


def test_experiment_cli_cannot_overwrite_input_or_config(
    chronological_csv: Path, tmp_path: Path
) -> None:
    data, _ = load_validated_csv(chronological_csv)
    config_path = tmp_path / "split.json"
    save_split_config(make_split_config(data, fingerprint(chronological_csv)), config_path)
    for protected in (chronological_csv, config_path):
        original = protected.read_bytes()
        assert (
            naive.main(
                [
                    "--dataset",
                    str(chronological_csv),
                    "--split-config",
                    str(config_path),
                    "--output",
                    str(protected),
                ]
            )
            == 2
        )
        assert protected.read_bytes() == original


def test_experiment_cli_rejects_changed_source_without_rewriting_report(
    chronological_csv: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data, _ = load_validated_csv(chronological_csv)
    config_path = tmp_path / "split.json"
    save_split_config(make_split_config(data, fingerprint(chronological_csv)), config_path)
    output = tmp_path / "EXP-001.md"
    output.write_text("existing evidence", encoding="utf-8")
    text = chronological_csv.read_text(encoding="utf-8").replace(",sewing,", ",sewing ,")
    chronological_csv.write_text(text, encoding="utf-8")
    # Whitespace normalization preserves values, but changed bytes invalidate the fingerprint.
    assert (
        naive.main(
            [
                "--dataset",
                str(chronological_csv),
                "--split-config",
                str(config_path),
                "--output",
                str(output),
            ]
        )
        == 2
    )
    assert "fingerprint" in capsys.readouterr().err
    assert output.read_text(encoding="utf-8") == "existing evidence"


def test_runtime_reporting_does_not_require_optional_development_tools(
    chronological_data: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = make_split_config(chronological_data, DIGEST)
    result = naive.run_experiment(chronological_data, config, dataset_sha256=DIGEST)
    real_version = reporting.version

    def runtime_version(package: str) -> str:
        if package in ("pytest", "ruff"):
            raise PackageNotFoundError(package)
        return real_version(package)

    monkeypatch.setattr(reporting, "version", runtime_version)
    from loometric.data.validation import ValidationResult

    report = reporting.render_report(
        result,
        ValidationResult(()),
        runtime_seconds=0.0,
        dataset_path=Path("synthetic.csv"),
        config_path=Path("synthetic-split.json"),
    )
    assert "not installed (optional development tool)" in report
