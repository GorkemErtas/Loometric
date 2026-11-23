from datetime import UTC, date, datetime, time, timedelta

import pandas as pd
import pytest

from loometric.ml_research.features import STAGES
from loometric.synthetic_ml.features import FEATURE_COLUMNS
from loometric.synthetic_ml.storage import digest
from loometric.synthetic_training.data import Population
from loometric.synthetic_training.models import workload_band


@pytest.fixture
def research_population():
    days = [date(2030, 1, 7) + timedelta(days=n) for n in range(36)]
    days = [day for day in days if day.weekday() != 6][:30]
    rows, records, labels, ids = [], [], [], []
    for number, day in enumerate(days):
        for stage in STAGES:
            for shift in ("day", "night"):
                workers = 4 + number % 3
                row = {
                    "stage": stage,
                    "shift_kind": shift,
                    "weekday": str(day.weekday()),
                    "planned_workers": float(workers),
                    "skill_level": 3.0,
                    "style_complexity": 2.0,
                    "standard_worker_minutes_per_piece": 2.5,
                    "planned_machine_available": 1.0,
                    "available_minutes": 420.0,
                    "planned_downtime_minutes": 30.0,
                    "opening_wip_pieces": 100.0,
                    "planned_release_pieces": 500.0 + number,
                    "order_quantity": 600.0 + number,
                }
                start = datetime.combine(day, time(8 if shift == "day" else 20), UTC)
                oid = f"PRIVATE-{day}-{stage}-{shift}"
                rows.append(row)
                ids.append(oid)
                labels.append(0.45 + number / 1000 + (0.01 if shift == "night" else 0))
                records.append(
                    {
                        "start_date": day,
                        "cutoff": start - timedelta(minutes=30),
                        "label_available_at": start + timedelta(hours=10),
                        "stage": stage,
                        "shift_kind": shift,
                        "staffing_band": "1-5" if workers <= 5 else "6-10",
                        "workload_band": workload_band(row),
                        "interruption_band": "1-30",
                        "low_demand": workload_band(row) == "low",
                        "demand_censored": False,
                        "planned_load_ratio": row["order_quantity"] * 2.5 / (420 * workers),
                    }
                )
    index = pd.Index(ids, name="observation_id")
    return Population(
        pd.DataFrame(rows, index=index, columns=FEATURE_COLUMNS),
        pd.Series(labels, index=index, name="standard_capacity_attainment"),
        pd.DataFrame(records, index=index),
        (),
        digest(rows),
    )
