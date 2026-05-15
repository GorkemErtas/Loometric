import pandas as pd
import pytest

from loometric.baselines import DepartmentMeanBaseline, GlobalMeanBaseline


def test_global_mean_is_training_only_and_preserves_prediction_index() -> None:
    model = GlobalMeanBaseline.fit(pd.Series([0.2, 0.6, 1.0]))
    assert model.mean == pytest.approx(0.6)
    index = pd.Index([100, 200, 300])
    predictions = model.predict(index)
    assert predictions.index.equals(index)
    assert predictions.tolist() == pytest.approx([0.6, 0.6, 0.6])


def test_department_means_and_global_fallback_for_unknown_or_missing_department() -> None:
    departments = pd.Series(["sewing", "finishing", "sewing", "finishing"])
    target = pd.Series([0.2, 0.6, 0.6, 1.0])
    model = DepartmentMeanBaseline.fit(departments, target)
    requested = pd.Series(["sewing", "finishing", "new-department", pd.NA], index=[9, 7, 5, 3])
    predictions = model.predict(requested)
    assert model.department_means == pytest.approx({"sewing": 0.4, "finishing": 0.8})
    assert predictions.tolist() == pytest.approx([0.4, 0.8, 0.6, 0.6])
    assert predictions.index.equals(requested.index)


@pytest.mark.parametrize("values", [[], [float("nan")], [float("inf")], [pd.NA], ["invalid"]])
def test_bad_training_targets_are_rejected(values: list[object]) -> None:
    with pytest.raises(ValueError):
        GlobalMeanBaseline.fit(pd.Series(values))


def test_department_training_requires_complete_aligned_labels() -> None:
    with pytest.raises(ValueError, match="aligned"):
        DepartmentMeanBaseline.fit(pd.Series(["sewing"], index=[1]), pd.Series([0.8], index=[2]))
    with pytest.raises(ValueError, match="complete"):
        DepartmentMeanBaseline.fit(pd.Series([pd.NA]), pd.Series([0.8]))
