import json
import subprocess
import sys
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from loometric.compatibility.assessment import assess_compatibility, context_fingerprint
from loometric.compatibility.contracts import (
    AssessmentRequest,
    CompatibilityStatus,
    EvidenceReference,
    Gate,
    GateStatus,
)
from loometric.scheduling.contracts import instance_fingerprint
from loometric.scheduling.loading import instance_json


def codes(result):
    return {code for check in result.mappings for code in check.reason_codes}


def test_matching_context_is_deterministic_and_blocked_without_target_semantics(
    request_context, model_profile, instance
):
    before = instance_json(instance)
    first = assess_compatibility(request_context, model_profile, instance)
    assert first == assess_compatibility(request_context, model_profile, instance)
    assert first.status == CompatibilityStatus.INSUFFICIENT_EVIDENCE
    assert first.target_to_efficiency == "BLOCKED" and first.converted_efficiency is None
    assert first.integration_readiness == "NOT_READY" and not first.capacity_application_authorized
    assert not first.final_test_evaluated
    assert "TARGET_FORMULA_DENOMINATOR_UNVERIFIED" in codes(first)
    assert first.provenance["instance_fingerprint"] == instance_fingerprint(instance)
    assert first.provenance["artifact_fingerprint"] == model_profile.artifact_fingerprint
    assert instance_json(instance) == before


@pytest.mark.parametrize("department", ["sewing", "finishing"])
def test_supported_names_need_process_evidence(
    request_context, model_profile, instance, department
):
    from loometric.planning.domain import Stage

    planning = instance.planning
    stage = Stage(department)
    order = replace(planning.orders[0], required_stages=(stage,))
    line = replace(planning.lines[0], stage=stage)
    cap = replace(planning.capabilities[0], stage=stage)
    changed = replace(
        instance, planning=replace(planning, orders=(order,), lines=(line,), capabilities=(cap,))
    )
    context = replace(
        request_context,
        prediction_request=replace(request_context.prediction_request, department=department),
    )
    result = assess_compatibility(context, model_profile, changed)
    mapping = next(m for m in result.mappings if m.name == "department_stage")
    assert mapping.status == CompatibilityStatus.CONDITIONAL
    assert result.status != CompatibilityStatus.COMPATIBLE


@pytest.mark.parametrize("stage", ["cutting", "quality_control", "packing", "finishing"])
def test_unsupported_or_cross_department_mapping_is_rejected(
    request_context, model_profile, instance, stage
):
    from loometric.planning.domain import Stage, StageStandard

    p = instance.planning
    target = Stage(stage)
    style = replace(p.styles[0], standards=(StageStandard(target, Decimal("1")),))
    order = replace(p.orders[0], required_stages=(target,))
    line = replace(p.lines[0], stage=target)
    cap = replace(p.capabilities[0], stage=target)
    instance = replace(
        instance,
        planning=replace(p, styles=(style,), orders=(order,), lines=(line,), capabilities=(cap,)),
    )
    result = assess_compatibility(request_context, model_profile, instance)
    assert result.status == CompatibilityStatus.INCOMPATIBLE
    assert "UNSUPPORTED_DEPARTMENT_STAGE_MAPPING" in codes(result)


def test_equal_numeric_team_and_line_ids_do_not_prove_crew_identity(
    request_context, model_profile, instance
):
    p = instance.planning
    p = replace(
        p,
        lines=(replace(p.lines[0], line_id="1"),),
        capacity_profiles=(replace(p.capacity_profiles[0], line_id="1"),),
        capabilities=(replace(p.capabilities[0], line_id="1"),),
        calendar=replace(
            p.calendar, assignments=(replace(p.calendar.assignments[0], line_id="1"),)
        ),
    )
    result = assess_compatibility(request_context, model_profile, replace(instance, planning=p))
    assert "TEAM_TO_DEDICATED_CREW_MAPPING_MISSING" in codes(result)
    assert result.status == CompatibilityStatus.INSUFFICIENT_EVIDENCE


def test_unknown_team_is_explicitly_unvalidated(request_context, model_profile, instance):
    request_context = replace(
        request_context, prediction_request=replace(request_context.prediction_request, team="999")
    )
    result = assess_compatibility(request_context, model_profile, instance)
    assert "UNKNOWN_TEAM_UNVALIDATED" in codes(result)
    assert (
        next(g for g in result.gates if g.gate == Gate.SUPPORTED_INPUTS).status
        == GateStatus.BLOCKED
    )


@pytest.mark.parametrize(
    "value",
    [Decimal("-0.1"), Decimal("NaN"), Decimal("Infinity"), Decimal("1.00000000000000000001"), None],
)
def test_invalid_or_unsupported_range_is_not_clamped(
    request_context, model_profile, instance, value
):
    result = assess_compatibility(
        replace(request_context, predicted_productivity=value), model_profile, instance
    )
    assert result.status == CompatibilityStatus.INCOMPATIBLE
    assert result.declared_prediction == (str(value) if value is not None else None)
    assert result.converted_efficiency is None
    assert (
        next(g for g in result.gates if g.gate == Gate.PREDICTION_RANGE).status == GateStatus.FAIL
    )
    assert instance.planning.capacity_profiles[0].assumed_efficiency == Decimal("0.8")


@pytest.mark.parametrize("grain", ["individual_worker", "order_stage", "line_stage_shift"])
def test_unestablished_grain_cannot_be_relabelled(request_context, model_profile, instance, grain):
    result = assess_compatibility(
        replace(request_context, observation_grain=grain), model_profile, instance
    )
    assert "DECLARED_GRAIN_UNSUPPORTED_BY_M01" in codes(result)
    assert result.status == CompatibilityStatus.INCOMPATIBLE


def test_all_asserted_references_cannot_fabricate_readiness(
    request_context, model_profile, instance
):
    context_hash = context_fingerprint(request_context, model_profile, instance)
    references = tuple(
        EvidenceReference(gate, "synthetic assertion, not source-owner approval", context_hash)
        for gate in Gate
    )
    result = assess_compatibility(
        replace(request_context, evidence_references=references), model_profile, instance
    )
    assert result.status == CompatibilityStatus.INSUFFICIENT_EVIDENCE
    assert next(g for g in result.gates if g.gate == Gate.TARGET_UNITS).status == GateStatus.BLOCKED
    assert (
        next(m for m in result.mappings if m.name == "team_crew").status
        == CompatibilityStatus.CONDITIONAL
    )
    for update in (
        {"integration_readiness": "READY"},
        {"capacity_application_authorized": True},
        {"target_to_efficiency": "ALLOWED"},
        {"converted_efficiency": Decimal("0.8")},
        {"status": CompatibilityStatus.COMPATIBLE},
        {"final_test_evaluated": True},
    ):
        with pytest.raises(ValueError):
            replace(result, **update)


def test_stale_evidence_and_model_identity_reject(request_context, model_profile, instance):
    context_hash = context_fingerprint(request_context, model_profile, instance)
    candidate = replace(
        request_context,
        evidence_references=(EvidenceReference(Gate.TEAM_CREW, "synthetic", context_hash),),
        predicted_productivity=Decimal("0.7"),
        artifact_fingerprint="e" * 64,
    )
    result = assess_compatibility(candidate, model_profile, instance)
    assert {"MODEL_IDENTITY_MISMATCH", "EVIDENCE_CONTEXT_MISMATCH"} <= codes(result)
    assert result.status == CompatibilityStatus.INCOMPATIBLE


@pytest.mark.parametrize(
    "change",
    [
        "after_start",
        "no_shift",
        "wrong_date",
        "training_overlap",
        "future_snapshot",
        "missing_assignment",
        "missing_order",
    ],
)
def test_invalid_prediction_time_and_planning_contexts(
    request_context, model_profile, instance, change
):
    source = request_context.prediction_request
    if change == "after_start":
        source = replace(source, prediction_cutoff=source.prediction_cutoff + timedelta(hours=2))
    elif change == "no_shift":
        source = replace(source, shift_id=None)
    elif change == "wrong_date":
        source = replace(source, scheduled_date=date(2030, 1, 8))
    elif change == "training_overlap":
        model_profile = replace(model_profile, training_end=source.scheduled_date)
    elif change == "future_snapshot":
        request_context = replace(
            request_context, as_of=source.source_snapshot_timestamp - timedelta(minutes=1)
        )
    elif change == "missing_assignment":
        request_context = replace(request_context, assignment_id="unknown")
    else:
        request_context = replace(request_context, order_id="unknown")
    result = assess_compatibility(
        replace(request_context, prediction_request=source), model_profile, instance
    )
    assert result.status == CompatibilityStatus.INCOMPATIBLE


def test_closed_json_numeric_and_version_contract(request_context):
    from dataclasses import asdict

    from loometric.planning.reporting import json_value

    payload = json_value(asdict(request_context))
    payload["predicted_productivity"] = 0.8
    for update in (
        {"schema_version": True},
        {"schema_version": 2},
        {"actual_productivity": 0.6},
        {"test_labels": [1]},
        {"predicted_productivity": "0.8"},
        {"predicted_productivity": True},
    ):
        with pytest.raises(ValueError):
            AssessmentRequest.from_json(json.dumps({**payload, **update}))
    for source in (
        '{"x":NaN}',
        '{"x":1,"x":2}',
        "[" * 25 + "0" + "]" * 25,
        " " * 262145,
        '{"x":1e99999999}',
    ):
        with pytest.raises(ValueError):
            AssessmentRequest.from_json(source)


def test_core_imports_without_ml_and_never_opens_data_or_loads_a_model():
    code = """
import sys
sys.path.insert(0,'src')
def guard(event,args):
    if event=='open' and isinstance(args[0],str):
        path=args[0].replace(chr(92),'/').lower()
        assert '/data/' not in path and not path.endswith(('.joblib','.csv')),path
sys.addaudithook(guard)
import loometric.compatibility
blocked={'pandas','numpy','sklearn','joblib','ortools','fastapi'}
assert not any(m.split('.')[0] in blocked for m in sys.modules)
"""
    completed = subprocess.run(
        [sys.executable, "-S", "-c", code],
        capture_output=True,
        text=True,
        timeout=20,
        cwd=Path(__file__).resolve().parents[2],
    )
    assert completed.returncode == 0, completed.stderr
