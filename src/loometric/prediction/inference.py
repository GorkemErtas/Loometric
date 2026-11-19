"""Pure offline inference from an explicitly loaded artifact; no fitting or file access."""

from datetime import datetime
from math import isfinite

import pandas as pd

from loometric.features import build_features
from loometric.prediction.artifacts import MODEL_ID, MODEL_VERSION, LoadedArtifact
from loometric.prediction.contracts import (
    INPUT_SCHEMA_VERSION,
    PredictionRequest,
    PredictionResult,
    PredictionStatus,
    Warning,
    require_aware,
)
from loometric.prediction.policy import ReviewPolicy, assess_request

LIMITATION = Warning(
    "EXPERIMENTAL_MODEL",
    "Historical 2015 data; temporal gains are inconsistent and live readiness is unverified. "
    "Human review is required. No staffing, scheduling or production authorization.",
)


def make_result(
    *,
    now: datetime,
    request: PredictionRequest | None = None,
    artifact: LoadedArtifact | None = None,
    replay_at: datetime | None = None,
    status: PredictionStatus = PredictionStatus.ABSTAIN,
    warnings: tuple[Warning, ...] = (),
    prediction: float | None = None,
    baseline: float | None = None,
) -> PredictionResult:
    require_aware(now)
    if replay_at is not None:
        require_aware(replay_at)
        warnings += (
            Warning("OFFLINE_REPLAY", "Reference time is explicitly simulated for offline replay."),
        )
        if status == PredictionStatus.VALID_EXPERIMENTAL:
            status = PredictionStatus.REVIEW_REQUIRED
    if status == PredictionStatus.ABSTAIN:
        prediction = baseline = None
    return PredictionResult(
        status=status,
        predicted_productivity=prediction,
        baseline_prediction=baseline,
        model_id=MODEL_ID if artifact else None,
        model_version=MODEL_VERSION if artifact else None,
        input_schema_version=INPUT_SCHEMA_VERSION,
        model_configuration_fingerprint=(
            artifact.manifest["model_configuration_fingerprint"] if artifact else None
        ),
        artifact_fingerprint=artifact.artifact_fingerprint if artifact else None,
        prediction_timestamp=now.isoformat(),
        as_of_timestamp=(replay_at or now).isoformat(),
        execution_mode="OFFLINE_REPLAY" if replay_at is not None else "CURRENT_CLOCK",
        source_provenance=request.provenance() if request else None,
        validation_warnings=(LIMITATION, *warnings),
    )


def predict(
    request: PredictionRequest,
    artifact: LoadedArtifact | None,
    *,
    now: datetime,
    policy: ReviewPolicy | None = None,
    replay_at: datetime | None = None,
) -> PredictionResult:
    """Produce a candidate plus baseline, or explicit abstention. Never authorizes decisions."""
    require_aware(now)
    as_of = replay_at or now
    require_aware(as_of)
    context = {"now": now, "request": request, "artifact": artifact, "replay_at": replay_at}
    if artifact is None:
        return make_result(
            **context, warnings=(Warning("ARTIFACT_MISSING", "No model was loaded."),)
        )
    training_end = artifact.manifest["lineage"]["training"]["end"]
    if (
        min(
            request.scheduled_date.isoformat(),
            request.prediction_cutoff.date().isoformat(),
            as_of.date().isoformat(),
        )
        <= training_end
    ):
        return make_result(
            **context,
            warnings=(
                Warning(
                    "MODEL_TEMPORAL_OVERLAP",
                    "Request/reference time must follow the artifact training period.",
                ),
            ),
        )
    categories = artifact.manifest["training_categories"]
    status, warnings = assess_request(
        request,
        policy or ReviewPolicy(),
        known_team=request.team in categories["team"],
        as_of=as_of,
    )
    if status == PredictionStatus.ABSTAIN:
        return make_result(**context, status=status, warnings=warnings)
    try:
        # Provenance, cutoff and shift ID are validation metadata, never estimator inputs.
        features = build_features(
            pd.DataFrame(
                {
                    "date": pd.to_datetime([request.scheduled_date.isoformat()]),
                    "department": [request.department],
                    "team": [request.team],
                }
            )
        )
        for column, values in categories.items():
            if column != "team" and str(features[column].iloc[0]) not in values:
                status = PredictionStatus.REVIEW_REQUIRED
                warnings += (
                    Warning("UNKNOWN_CATEGORY", f"Unseen training category for {column}."),
                )
        prediction = float(artifact.pipeline.predict(features)[0])
        baseline = float(artifact.baseline.predict(features["department"]).iloc[0])
        if not all(isfinite(value) and value >= 0 for value in (prediction, baseline)):
            raise ValueError("Model output is not finite and nonnegative.")
        if prediction > 1 or baseline > 1:
            status = PredictionStatus.REVIEW_REQUIRED
            warnings += (
                Warning("PREDICTION_ABOVE_ONE", "Productivity above one is retained, not clipped."),
            )
        return make_result(
            **context, status=status, warnings=warnings, prediction=prediction, baseline=baseline
        )
    except (ValueError, TypeError, OverflowError) as exc:
        return make_result(**context, warnings=(Warning("INFERENCE_FAILED", str(exc)),))
