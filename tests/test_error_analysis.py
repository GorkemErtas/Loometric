from math import sqrt

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from loometric.error_analysis import (
    ANALYZED_MODELS,
    analyze_errors,
    build_error_rows,
    grouped_error_summaries,
    summarize_errors,
)


@pytest.fixture
def population() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2015-01-01", "2015-01-01", "2015-01-02", "2015-01-02"]),
            "fold": ["F01", "F01", "F02", "F02"],
            "department": ["sewing", "finishing", "sewing", "finishing"],
            "team": ["1", "1", "1", "1"],
            "actual": [0.5] * 4,
        },
        index=[10, 20, 30, 40],
    )


@pytest.fixture
def predictions(population: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        name: pd.Series([0.5, 0.6, 0.2, 1.1], index=population.index) for name in ANALYZED_MODELS
    }


def test_errors_quantiles_and_concentration_match_hand_calculations(
    population: pd.DataFrame, predictions: dict[str, pd.Series]
) -> None:
    rows = build_error_rows(population, predictions)
    summary = summarize_errors(rows.loc[rows["model"].eq("department_mean")])
    assert summary.metrics.samples == 4
    assert summary.metrics.mae == pytest.approx(0.25)
    assert summary.metrics.rmse == pytest.approx(sqrt(0.46 / 4))
    assert summary.metrics.bias == pytest.approx(0.1)
    assert summary.metrics.r2 is None
    assert summary.absolute_quantiles["0.5"] == pytest.approx(0.2)
    assert summary.absolute_quantiles["0.9"] == pytest.approx(0.51)
    assert summary.high_error_rows == 2 and summary.high_error_fraction == 0.5
    assert summary.observed_dates == 2 and summary.low_support
    for tail in summary.concentration.values():
        assert tail.rows == 1
        assert tail.absolute_error_share == pytest.approx(0.6)
        assert tail.squared_error_share == pytest.approx(0.36 / 0.46)
        assert tail.remaining_mae == pytest.approx(0.4 / 3)


def test_group_sizes_do_not_duplicate_targets_or_merge_department_team_ids(
    population: pd.DataFrame, predictions: dict[str, pd.Series]
) -> None:
    result = analyze_errors(population, predictions)
    assert result["population_rows"] == result["target_distribution"]["samples"] == 4
    assert len(result["team_stability"]) == 2
    assert {entry["department"] for entry in result["team_stability"]} == {"sewing", "finishing"}
    assert sum(entry["samples"] for entry in result["team_stability"]) == 4
    for entry in result["team_stability"]:
        assert entry["min_window_samples"] == 1
        assert entry["windows_present"] == entry["total_windows"] == 2
        assert entry["low_window_support"]
    for entry in result["summaries"]["team"]:
        assert entry["summary"]["metrics"]["samples"] == 2
        assert entry["summary"]["low_support"]


def test_common_tail_sensitivity_uses_identical_rows_for_all_models(
    population: pd.DataFrame, predictions: dict[str, pd.Series]
) -> None:
    predictions["linear_A"] = pd.Series([0.0, 0.5, 0.5, 0.5], index=population.index)
    result = analyze_errors(population, predictions)
    sensitivity = result["common_tail_sensitivity"]
    assert sensitivity["excluded_rows"] == 1 and sensitivity["remaining_rows"] == 3
    for metrics in sensitivity["remaining_metrics"].values():
        assert metrics["samples"] == 3
    assert sensitivity["remaining_metrics"]["linear_A"]["mae"] == pytest.approx(0.5 / 3)
    assert all(
        entry["summary"]["metrics"]["samples"] == 4 for entry in result["summaries"]["overall"]
    )


def test_zero_errors_and_singletons_do_not_invent_concentration_or_r2(
    population: pd.DataFrame,
) -> None:
    single = population.iloc[:1]
    predictions = {name: single["actual"].copy() for name in ANALYZED_MODELS}
    result = analyze_errors(single, predictions)
    for entry in result["summaries"]["overall"]:
        summary = entry["summary"]
        assert summary["metrics"]["mae"] == 0 and summary["metrics"]["r2"] is None
        for tail in summary["concentration"].values():
            assert tail["absolute_error_share"] is tail["squared_error_share"] is None
            assert tail["remaining_mae"] is None
    assert result["common_tail_sensitivity"]["remaining_rows"] == 0


def test_small_group_flag_and_observed_window_coverage_are_explicit(
    population: pd.DataFrame,
) -> None:
    repeated = pd.concat([population.iloc[[0]]] * 20, ignore_index=True)
    repeated["fold"] = "F01"
    predictions = {name: repeated["actual"] + 0.1 for name in ANALYZED_MODELS}
    result = analyze_errors(repeated, predictions)
    assert not result["summaries"]["overall"][0]["summary"]["low_support"]
    assert result["summaries"]["overall"][0]["summary"]["observed_dates"] == 1
    sparse = population.iloc[[0, 1, 3]]
    sparse_predictions = {name: sparse["actual"] for name in ANALYZED_MODELS}
    entries = analyze_errors(sparse, sparse_predictions)["team_stability"]
    sewing = next(entry for entry in entries if entry["department"] == "sewing")
    assert sewing["windows_present"] == 1 and sewing["total_windows"] == 2


def test_diagnostics_are_reproducible_and_do_not_mutate_inputs(
    population: pd.DataFrame, predictions: dict[str, pd.Series]
) -> None:
    original = population.copy(deep=True)
    first = analyze_errors(population, predictions)
    assert analyze_errors(population, predictions) == first
    assert_frame_equal(population, original)
    rows = build_error_rows(population, predictions)
    grouped = grouped_error_summaries(rows, ("model", "fold"))
    for name in ANALYZED_MODELS:
        assert (
            sum(
                entry["summary"]["metrics"]["samples"]
                for entry in grouped
                if entry["group"]["model"] == name
            )
            == 4
        )


@pytest.mark.parametrize("kind", ["missing", "misaligned", "nonfinite", "incomplete", "duplicate"])
def test_invalid_or_misaligned_analysis_inputs_fail_without_dropping_rows(
    population: pd.DataFrame, predictions: dict[str, pd.Series], kind: str
) -> None:
    if kind == "missing":
        predictions.pop("linear_A")
    elif kind == "misaligned":
        predictions["linear_A"].index = [11, 21, 31, 41]
    elif kind == "nonfinite":
        predictions["linear_A"].iloc[0] = float("inf")
    elif kind == "incomplete":
        population.loc[10, "team"] = None
    else:
        population.index = [10] * len(population)
    with pytest.raises(ValueError):
        analyze_errors(population, predictions)
