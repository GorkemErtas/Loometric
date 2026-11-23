"""Stateless pre-shift units and interactions; no outcome, entity or scenario access."""

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

from loometric.synthetic_ml.features import FEATURE_COLUMNS
from loometric.synthetic_training.data import require
from loometric.synthetic_training.models import validate_matrix

STAGES = ("cutting", "sewing", "finishing", "quality_control", "packing")
DERIVED_UNITS = {
    "planned_worker_minutes": "worker_minute",
    "planned_load_ratio": "standard_worker_minute_per_worker_minute",
    "one_piece_attainment_quantum": "standard_worker_minute_per_worker_minute",
    "skill_complexity_interaction": "declared_ordinal_level_product_not_physical_scale",
    "opening_wip_share": "piece_per_piece",
    "planned_downtime_fraction": "minute_per_480_minute_shift",
    **{f"load_at_{stage}": "standard_worker_minute_per_worker_minute" for stage in STAGES},
}


class PlannedFeatures(TransformerMixin, BaseEstimator):
    def fit(self, X, y=None):
        self.transform(X)
        self.feature_names_in_ = np.asarray(FEATURE_COLUMNS, dtype=object)
        return self

    def transform(self, X):
        validate_matrix(X)
        budget = X.available_minutes * X.planned_workers
        require(
            (budget > 0).all() and (X.order_quantity > 0).all(), "DEFINED_PLANNED_CAPACITY_REQUIRED"
        )
        require(
            (X.opening_wip_pieces + X.planned_release_pieces == X.order_quantity).all(),
            "PLANNED_STOCK_IDENTITY_REQUIRED",
        )
        result = X.copy()
        result["planned_worker_minutes"] = budget
        result["planned_load_ratio"] = (
            X.order_quantity * X.standard_worker_minutes_per_piece / budget
        )
        result["one_piece_attainment_quantum"] = X.standard_worker_minutes_per_piece / budget
        result["skill_complexity_interaction"] = X.skill_level * X.style_complexity
        result["opening_wip_share"] = X.opening_wip_pieces / X.order_quantity
        result["planned_downtime_fraction"] = X.planned_downtime_minutes / 480
        for stage in STAGES:
            result[f"load_at_{stage}"] = result.planned_load_ratio * X.stage.eq(stage)
        require(
            np.isfinite(result.loc[:, list(DERIVED_UNITS)].to_numpy()).all(),
            "FINITE_DERIVED_FEATURES_REQUIRED",
        )
        return result

    def get_feature_names_out(self, input_features=None):
        return np.asarray((*FEATURE_COLUMNS, *DERIVED_UNITS), dtype=object)
