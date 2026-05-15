from math import sqrt

import pandas as pd
import pytest

from loometric.evaluation import regression_metrics


def test_metrics_match_hand_calculated_errors_and_positive_overprediction_bias() -> None:
    metrics = regression_metrics(pd.Series([1.0, 2.0, 3.0]), pd.Series([2.0, 2.0, 5.0]))
    assert metrics.samples == 3
    assert metrics.mae == pytest.approx(1.0)
    assert metrics.rmse == pytest.approx(sqrt(5 / 3))
    assert metrics.r2 == pytest.approx(-1.5)
    assert metrics.bias == pytest.approx(1.0)


def test_perfect_predictions_have_no_errors() -> None:
    values = pd.Series([0.3, 0.7, 1.1])
    metrics = regression_metrics(values, values.copy())
    assert (metrics.mae, metrics.rmse, metrics.r2, metrics.bias) == (0, 0, 1, 0)


@pytest.mark.parametrize("values", [[0.5], [0.5, 0.5]])
def test_r2_is_explicitly_undefined_for_insufficient_or_constant_targets(
    values: list[float],
) -> None:
    metrics = regression_metrics(pd.Series(values), pd.Series(values))
    assert metrics.r2 is None
    assert metrics.mae == 0


@pytest.mark.parametrize(
    ("actual", "predicted"),
    [
        ([], []),
        ([0.2], [0.2, 0.3]),
        ([float("nan")], [0.2]),
        ([0.2], [float("inf")]),
        ([pd.NA], [0.2]),
    ],
)
def test_bad_metric_inputs_are_not_silently_dropped(
    actual: list[object], predicted: list[object]
) -> None:
    with pytest.raises(ValueError):
        regression_metrics(pd.Series(actual), pd.Series(predicted))


def test_misaligned_indices_are_rejected_instead_of_pandas_alignment() -> None:
    with pytest.raises(ValueError, match="indexed"):
        regression_metrics(pd.Series([0.5], index=[1]), pd.Series([0.5], index=[2]))
