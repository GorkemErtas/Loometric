"""Pure declared-context checks; no fitting, inference, scheduling, conversion or I/O."""

from dataclasses import asdict

from loometric.compatibility.contracts import (
    M01_GRAIN,
    AssessmentRequest,
    CompatibilityAssessment,
    Gate,
    GateStatus,
    MappingCheck,
    ModelProfile,
    ReadinessGate,
    sha256_value,
)
from loometric.compatibility.contracts import (
    CompatibilityStatus as Status,
)
from loometric.prediction.contracts import PredictionStatus
from loometric.scheduling.contracts import SchedulingInstance, instance_fingerprint


def context_fingerprint(
    request: AssessmentRequest, model: ModelProfile, instance: SchedulingInstance
) -> str:
    value = asdict(request)
    value.pop("evidence_references")
    return sha256_value(
        {
            "policy": "m01-planning-audit-v1",
            "request": value,
            "model": asdict(model),
            "instance_fingerprint": instance_fingerprint(instance),
        }
    )


def assess_compatibility(
    request: AssessmentRequest, model: ModelProfile, instance: SchedulingInstance
) -> CompatibilityAssessment:
    if (
        not isinstance(request, AssessmentRequest)
        or not isinstance(model, ModelProfile)
        or not isinstance(instance, SchedulingInstance)
    ):
        raise TypeError("Assessment requires the typed offline contracts.")
    context_hash = context_fingerprint(request, model, instance)
    checks: list[MappingCheck] = []

    def add(name: str, status: Status, *codes: str) -> None:
        checks.append(MappingCheck(name, status, codes))

    bound = (
        request.artifact_fingerprint == model.artifact_fingerprint
        and request.model_configuration_fingerprint == model.model_configuration_fingerprint
    )
    add(
        "model_identity",
        Status.COMPATIBLE if bound else Status.INCOMPATIBLE,
        "MODEL_METADATA_BOUND" if bound else "MODEL_IDENTITY_MISMATCH",
    )
    references_valid = all(
        ref.context_fingerprint == context_hash for ref in request.evidence_references
    )
    add(
        "evidence_binding",
        Status.COMPATIBLE if references_valid else Status.INCOMPATIBLE,
        "REFERENCES_CONTEXT_BOUND" if references_valid else "EVIDENCE_CONTEXT_MISMATCH",
    )
    value = request.predicted_productivity
    in_range = value is not None and value.is_finite() and 0 <= value <= 1
    if value is None or request.prediction_status == PredictionStatus.ABSTAIN:
        add("prediction_range", Status.INCOMPATIBLE, "PREDICTION_UNAVAILABLE")
    elif not value.is_finite() or value < 0:
        add("prediction_range", Status.INCOMPATIBLE, "INVALID_PRODUCTIVITY_VALUE")
    elif value > 1:
        add(
            "prediction_range",
            Status.INCOMPATIBLE,
            "PRODUCTIVITY_ABOVE_PLANNING_RANGE",
            "NO_CLAMPING_PERMITTED",
        )
    else:
        add("prediction_range", Status.CONDITIONAL, "NUMERIC_RANGE_ALONE_IS_NOT_UNIT_COMPATIBILITY")
    source = request.prediction_request
    known_team = source.team in model.teams
    add(
        "known_team",
        Status.CONDITIONAL if known_team else Status.INSUFFICIENT_EVIDENCE,
        "KNOWN_CATEGORY_IS_NOT_CREW_IDENTITY" if known_team else "UNKNOWN_TEAM_UNVALIDATED",
    )
    known_weekday = str(source.scheduled_date.weekday()) in model.weekdays
    add(
        "calendar_category",
        Status.CONDITIONAL if known_weekday else Status.INSUFFICIENT_EVIDENCE,
        "SEEN_CALENDAR_CATEGORY_NOT_DOMAIN_VALIDATION"
        if known_weekday
        else "UNSEEN_WEEKDAY_CATEGORY",
    )
    if request.observation_grain == M01_GRAIN:
        add("observation_grain", Status.INSUFFICIENT_EVIDENCE, "SOURCE_SHIFT_GRAIN_UNVERIFIED")
    else:
        add("observation_grain", Status.INCOMPATIBLE, "DECLARED_GRAIN_UNSUPPORTED_BY_M01")
    temporal = (
        min(source.scheduled_date, source.prediction_cutoff.date(), request.as_of.date())
        > model.training_end
    )
    temporal = (
        temporal and source.source_snapshot_timestamp <= request.as_of <= source.prediction_cutoff
    )
    add(
        "prediction_timestamps",
        Status.COMPATIBLE if temporal else Status.INCOMPATIBLE,
        "DECLARED_TIMESTAMP_ORDER_VALID" if temporal else "TEMPORAL_CONTEXT_INVALID",
    )
    planning = instance.planning
    assignment = next(
        (a for a in planning.calendar.assignments if a.assignment_id == request.assignment_id), None
    )
    order = next((o for o in planning.orders if o.order_id == request.order_id), None)
    if assignment is None or order is None:
        add("planning_references", Status.INCOMPATIBLE, "UNKNOWN_PLANNING_REFERENCE")
    else:
        line = next(item for item in planning.lines if item.line_id == assignment.line_id)
        shift = next(s for s in planning.shifts if s.shift_id == assignment.shift_id)
        stage_match = (
            line.stage.value == source.department and source.department in model.departments
        )
        add(
            "department_stage",
            Status.CONDITIONAL if stage_match else Status.INCOMPATIBLE,
            "LABEL_MATCH_REQUIRES_PROCESS_EVIDENCE"
            if stage_match
            else "UNSUPPORTED_DEPARTMENT_STAGE_MAPPING",
        )
        calendar_match = (
            source.scheduled_date == shift.interval.start.date()
            and source.shift_id == shift.shift_id
            and source.prediction_cutoff < shift.interval.start
        )
        add(
            "shift_context",
            Status.COMPATIBLE if calendar_match else Status.INCOMPATIBLE,
            "DECLARED_SHIFT_CONTEXT_MATCHES"
            if calendar_match
            else "SHIFT_DATE_ID_OR_PRE_SHIFT_CUTOFF_MISMATCH",
        )
        qualified = line.stage in order.required_stages and any(
            c.line_id == line.line_id and c.style_id == order.style_id and c.stage == line.stage
            for c in planning.capabilities
        )
        add(
            "planning_capability",
            Status.COMPATIBLE if qualified else Status.INCOMPATIBLE,
            "EXPLICIT_SYNTHETIC_CAPABILITY_PRESENT"
            if qualified
            else "ORDER_STAGE_CAPABILITY_MISSING",
        )
    ref_gates = {
        ref.gate for ref in request.evidence_references if ref.context_fingerprint == context_hash
    }
    add(
        "team_crew",
        Status.CONDITIONAL if Gate.TEAM_CREW in ref_gates else Status.INSUFFICIENT_EVIDENCE,
        "CREW_REFERENCE_ASSERTED_NOT_VERIFIED"
        if Gate.TEAM_CREW in ref_gates
        else "TEAM_TO_DEDICATED_CREW_MAPPING_MISSING",
    )
    add(
        "target_to_efficiency",
        Status.INSUFFICIENT_EVIDENCE,
        "TARGET_FORMULA_DENOMINATOR_UNVERIFIED",
        "NO_APPROVED_WORKER_MINUTE_CONVERSION",
    )
    add(
        "style_standards_and_counterfactuals",
        Status.INSUFFICIENT_EVIDENCE,
        "STYLE_CREW_AND_STAGE_STANDARDS_NOT_MODEL_INPUTS",
        "NO_CAUSAL_CAPACITY_RESPONSE_ESTABLISHED",
    )
    gates = (
        (Gate.TARGET_UNITS, GateStatus.BLOCKED, ("TARGET_FORMULA_DENOMINATOR_UNVERIFIED",)),
        (
            Gate.FEATURE_TIMING,
            GateStatus.BLOCKED,
            ("SOURCE_CAPTURE_REVISION_AND_LABEL_LATENCY_MISSING",),
        ),
        (
            Gate.DEPARTMENT_STAGE,
            GateStatus.FAIL
            if any(m.name == "department_stage" and m.status == Status.INCOMPATIBLE for m in checks)
            else GateStatus.BLOCKED,
            ("SOURCE_PROCESS_TAXONOMY_UNVERIFIED",),
        ),
        (
            Gate.TEAM_CREW,
            GateStatus.BLOCKED,
            ("EFFECTIVE_ROSTER_AND_QUALIFICATION_MAPPING_MISSING",),
        ),
        (Gate.OBSERVATION_GRAIN, GateStatus.BLOCKED, ("SOURCE_SHIFT_GRAIN_UNVERIFIED",)),
        (Gate.DOMAIN_SHIFT, GateStatus.BLOCKED, ("NO_INDEPENDENT_PLANNING_DOMAIN_VALIDATION",)),
        (
            Gate.MODEL_QUALITY,
            GateStatus.FAIL,
            ("EXP004_FOREST_POOLED_MAE_WORSE_THAN_DEPARTMENT_BASELINE",),
        ),
        (
            Gate.UNCERTAINTY,
            GateStatus.NOT_ASSESSED,
            ("NO_CALIBRATED_UNCERTAINTY_OR_APPROVED_ERROR_TOLERANCE",),
        ),
        (
            Gate.ARTIFACT,
            GateStatus.PASS if bound else GateStatus.FAIL,
            ("METADATA_DIGEST_BINDING_ONLY_NOT_MODEL_EXECUTION",),
        ),
        (
            Gate.SUPPORTED_INPUTS,
            GateStatus.FAIL
            if not temporal
            else GateStatus.PASS
            if known_team and known_weekday
            else GateStatus.BLOCKED,
            ("M01_CLOSED_INPUT_CONTRACT_ONLY",),
        ),
        (
            Gate.PREDICTION_RANGE,
            GateStatus.BLOCKED
            if in_range and request.prediction_status != PredictionStatus.ABSTAIN
            else GateStatus.FAIL,
            ("RANGE_HANDLING_EXISTS_CONVERSION_REMAINS_UNSUPPORTED",),
        ),
        (
            Gate.OPERATIONAL_SAFETY,
            GateStatus.NOT_ASSESSED,
            ("NO_APPROVED_MONITORING_FALLBACK_OR_ROLLBACK_POLICY",),
        ),
    )
    results = tuple(
        ReadinessGate(
            gate,
            status,
            codes,
            tuple(
                ref.reference
                for ref in request.evidence_references
                if ref.gate == gate and ref.context_fingerprint == context_hash
            ),
        )
        for gate, status, codes in gates
    )
    overall = (
        Status.INCOMPATIBLE
        if any(c.status == Status.INCOMPATIBLE for c in checks)
        else Status.INSUFFICIENT_EVIDENCE
    )
    return CompatibilityAssessment(
        status=overall,
        mappings=tuple(checks),
        gates=results,
        provenance={
            "context_fingerprint": context_hash,
            "assessment_request_fingerprint": sha256_value(asdict(request)),
            "instance_id": instance.instance_id,
            "instance_fingerprint": instance_fingerprint(instance),
            "artifact_fingerprint": model.artifact_fingerprint,
            "model_configuration_fingerprint": model.model_configuration_fingerprint,
            "dataset_sha256": model.dataset_sha256,
            "split_file_sha256": model.split_file_sha256,
            "pipeline_sha256": model.pipeline_sha256,
            "model_id": model.model_id,
            "model_version": model.model_version,
            "source_id": source.source_id,
        },
        declared_prediction=str(value) if value is not None else None,
    )
