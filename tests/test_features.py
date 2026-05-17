import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from loometric.data.schema import COLUMNS
from loometric.features import FEATURE_SETS, SOURCE_COLUMNS, build_features, validate_feature_names
from loometric.leakage import FEATURE_POLICIES


def test_calendar_is_derived_and_team_is_an_identifier(chronological_data: pd.DataFrame) -> None:
    scheduled = chronological_data.loc[:, SOURCE_COLUMNS].copy()
    original = scheduled.copy(deep=True)
    features = build_features(scheduled)
    assert features.index.equals(scheduled.index)
    assert len(features) == len(scheduled)
    assert features.iloc[0].to_dict() == {
        "department": "sewing",
        "team": "1",
        "day_of_week": "3",
        "day_of_month": 1.0,
    }
    assert features.iloc[2]["day_of_week"] == "4"
    assert features.iloc[2]["day_of_month"] == 2
    assert features["team"].map(type).eq(str).all()
    assert_frame_equal(scheduled, original)


@pytest.mark.parametrize("column", [name for name in COLUMNS if name not in SOURCE_COLUMNS])
def test_feature_builder_rejects_every_unapproved_source_input(
    chronological_data: pd.DataFrame, column: str
) -> None:
    with pytest.raises(ValueError, match="only date, department, and team"):
        build_features(chronological_data.loc[:, (*SOURCE_COLUMNS, column)])


@pytest.mark.parametrize(
    "column", [policy.name for policy in FEATURE_POLICIES if policy.availability != "pre_shift"]
)
def test_model_feature_allowlist_rejects_conditional_realized_and_target_fields(
    column: str,
) -> None:
    with pytest.raises(ValueError, match="eligible"):
        validate_feature_names(("department", column))


@pytest.mark.parametrize("columns", [(), ("team", "team"), ("day",), ("date",), ("unknown",)])
def test_feature_allowlist_rejects_invalid_selections(columns: tuple[str, ...]) -> None:
    with pytest.raises(ValueError):
        validate_feature_names(columns)


def test_comparison_plan_is_small_and_fixed() -> None:
    assert FEATURE_SETS == (
        ("department_only", ("department",)),
        ("team_only", ("team",)),
        ("department_team", ("department", "team")),
        ("department_team_calendar", ("department", "team", "day_of_week", "day_of_month")),
    )


@pytest.mark.parametrize("value", [pd.NA, 0, -1, 1.5, float("inf"), "not-an-id"])
def test_team_ids_are_not_silently_imputed_or_rounded(
    chronological_data: pd.DataFrame, value: object
) -> None:
    scheduled = chronological_data.loc[:, SOURCE_COLUMNS].copy()
    scheduled["team"] = scheduled["team"].astype(object)
    scheduled.loc[0, "team"] = value
    with pytest.raises(ValueError):
        build_features(scheduled)


@pytest.mark.parametrize("kind", ["missing", "text", "time", "timezone", "department", "empty"])
def test_invalid_snapshots_fail_explicitly(chronological_data: pd.DataFrame, kind: str) -> None:
    scheduled = chronological_data.loc[:, SOURCE_COLUMNS].copy()
    if kind == "missing":
        scheduled.loc[0, "date"] = pd.NaT
    elif kind == "text":
        scheduled["date"] = scheduled["date"].astype(str)
    elif kind == "time":
        scheduled.loc[0, "date"] += pd.Timedelta(hours=1)
    elif kind == "timezone":
        scheduled["date"] = scheduled["date"].dt.tz_localize("UTC")
    elif kind == "department":
        scheduled.loc[0, "department"] = " "
    else:
        scheduled = scheduled.iloc[:0]
    with pytest.raises(ValueError):
        build_features(scheduled)
