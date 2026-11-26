"""Timestamped past-shift summaries; current/future labels cannot enter predictors."""

from dataclasses import dataclass
from datetime import datetime
from math import fsum, sqrt

from loometric.prospective_evaluation.source import require

HISTORY_COLUMNS = (
    "recent_attainment_mean",
    "recent_attainment_std",
    "history_count",
    "uncensored_history_count",
    "history_age_hours",
)


@dataclass(frozen=True)
class MatureObservation:
    observation_id: str
    crew_id: str
    line_id: str
    shift_start: datetime
    available_at: datetime
    attainment: float
    censored: bool


def history_snapshot(
    records: list[MatureObservation],
    *,
    crew_id: str,
    line_id: str,
    observation_id: str,
    shift_start: datetime,
    cutoff: datetime,
) -> dict:
    require(cutoff.tzinfo is not None and cutoff < shift_start, "AWARE_PRE_SHIFT_CUTOFF_REQUIRED")
    eligible = sorted(
        (
            r
            for r in records
            if r.crew_id == crew_id
            and r.line_id == line_id
            and r.observation_id != observation_id
            and r.available_at <= cutoff
            and r.shift_start < shift_start
        ),
        key=lambda r: (r.shift_start, r.observation_id),
    )[-7:]
    usable = [r.attainment for r in eligible if not r.censored]
    mean = fsum(usable) / len(usable) if len(usable) >= 2 else None
    std = sqrt(fsum((v - mean) ** 2 for v in usable) / len(usable)) if mean is not None else None
    return {
        "recent_attainment_mean": mean,
        "recent_attainment_std": std,
        "history_count": len(eligible),
        "uncensored_history_count": len(usable),
        "history_age_hours": (cutoff - max(r.available_at for r in eligible)).total_seconds() / 3600
        if eligible
        else None,
        "source_observation_ids": [r.observation_id for r in eligible],
        "latest_available_at": max(r.available_at for r in eligible).isoformat()
        if eligible
        else None,
    }
