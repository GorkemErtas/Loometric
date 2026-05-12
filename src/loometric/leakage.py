"""Document the prediction-time contract; this module does not build model features."""

from dataclasses import dataclass
from typing import Literal

Availability = Literal["pre_shift", "conditional", "post_shift", "target"]


@dataclass(frozen=True)
class FeaturePolicy:
    name: str
    availability: Availability
    reason: str


FEATURE_POLICIES = (
    FeaturePolicy("date", "pre_shift", "Shift date is known; also the future split boundary."),
    FeaturePolicy(
        "quarter",
        "conditional",
        "Source means a within-month bucket, not a calendar quarter; verify and derive from date.",
    ),
    FeaturePolicy(
        "department", "pre_shift", "Scheduled department; normalize sweing and whitespace."
    ),
    FeaturePolicy("day", "pre_shift", "Known calendar value; derive from the scheduled date."),
    FeaturePolicy("team", "pre_shift", "Scheduled team identity; treat as categorical."),
    FeaturePolicy(
        "targeted_productivity",
        "conditional",
        "Use only a frozen target set before the shift; later revisions would leak information.",
    ),
    FeaturePolicy(
        "smv",
        "conditional",
        "Use only the standard minute value of the style assigned before the shift.",
    ),
    FeaturePolicy(
        "wip",
        "conditional",
        "Measurement time is unknown; only a verified opening backlog snapshot is eligible.",
    ),
    FeaturePolicy(
        "over_time",
        "post_shift",
        "Realized overtime is not known before the shift; planned overtime needs a separate field.",
    ),
    FeaturePolicy(
        "incentive",
        "post_shift",
        "Realized payment can depend on output; a preannounced incentive plan is a separate field.",
    ),
    FeaturePolicy("idle_time", "post_shift", "Downtime accumulates during the shift."),
    FeaturePolicy("idle_men", "post_shift", "Idle staffing is observed during the shift."),
    FeaturePolicy(
        "no_of_style_change",
        "conditional",
        "A realized count is unavailable; require a frozen planned style-change count.",
    ),
    FeaturePolicy(
        "no_of_workers",
        "conditional",
        "Require planned staffing, not realized attendance or a shift-average headcount.",
    ),
    FeaturePolicy(
        "actual_productivity", "target", "Post-shift outcome; never an input for the same shift."
    ),
)


def leakage_markdown() -> str:
    """Render the conservative policy used in documentation and data profiles."""
    rows = [
        "| Column | Availability | Pre-shift interpretation |",
        "| --- | --- | --- |",
    ]
    rows.extend(f"| {p.name} | {p.availability} | {p.reason} |" for p in FEATURE_POLICIES)
    rows.extend(
        [
            "",
            "Only `pre_shift` fields are eligible by default. `conditional` fields remain excluded "
            "until their timestamps and business definitions are verified. `post_shift` fields and "
            "the target are excluded. These are conservative availability assumptions, not facts "
            "established by this CSV, which has no measurement timestamps.",
            "",
            "Future evaluation must use strictly increasing date blocks with every record from a "
            "date in the same partition. Do not randomly split rows: teams repeat, and same-date "
            "shifts share context. Fit any imputation, encoding, scaling, or selection on the "
            "training period only. No split or preprocessing fit is performed in this task.",
        ]
    )
    return "\n".join(rows)
