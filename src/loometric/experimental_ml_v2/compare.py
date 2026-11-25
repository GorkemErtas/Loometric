"""Offline comparison of frozen experimental estimators."""

import json
from math import isfinite

import pandas as pd
from threadpoolctl import threadpool_limits

from loometric.api.prediction_service import trusted_receipt
from loometric.experimental_ml.artifacts import load_trusted
from loometric.experimental_ml_v2.artifacts import (
    load_trusted_offline,
)
from loometric.synthetic_ml.features import FEATURE_COLUMNS


def compare() -> dict:
    _, existing_models = load_trusted(trusted_receipt())
    _, research_model = load_trusted_offline()

    models = {
        **existing_models,
        "rf_physics": research_model,
    }

    base_inputs = {
        "stage": "sewing",
        "shift_kind": "day",
        "weekday": "0",
        "planned_workers": 6,
        "skill_level": 3,
        "style_complexity": 3,
        "standard_worker_minutes_per_piece": 4.0,
        "planned_machine_available": 1,
        "available_minutes": 420,
        "planned_downtime_minutes": 30,
        "opening_wip_pieces": 100,
        "planned_release_pieces": 500,
        "order_quantity": 600,
    }

    scenarios = {
        "baseline": {},
        "increased_staffing": {
            "planned_workers": 8,
        },
        "increased_workload": {
            "planned_release_pieces": 700,
            "order_quantity": 800,
        },
        "increased_downtime": {
            "available_minutes": 360,
            "planned_downtime_minutes": 90,
        },
    }

    results = {}

    with threadpool_limits(limits=1):
        for scenario, changes in scenarios.items():
            inputs = {**base_inputs, **changes}

            frame = pd.DataFrame(
                [inputs],
                columns=FEATURE_COLUMNS,
            )

            predictions = {}

            for name, model in models.items():
                value = float(model.predict(frame)[0])

                if not isfinite(value):
                    raise ValueError(f"Non-finite prediction: {name}")

                predictions[name] = round(value, 8)

            results[scenario] = {
                "inputs": inputs,
                "predictions": predictions,
            }

    return {
        "target": "standard_capacity_attainment",
        "synthetic": True,
        "experimental_only": True,
        "promotion_decision": "NO_ML_PROMOTION",
        "scenarios": results,
    }


if __name__ == "__main__":
    print(json.dumps(compare(), indent=2))
