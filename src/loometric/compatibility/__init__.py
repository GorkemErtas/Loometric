"""Offline ML/planning compatibility; never applies predictions to capacity."""

from loometric.compatibility.assessment import assess_compatibility
from loometric.compatibility.contracts import (
    AssessmentRequest,
    CompatibilityStatus,
    GateStatus,
    ModelProfile,
)

__all__ = [
    "AssessmentRequest",
    "CompatibilityStatus",
    "GateStatus",
    "ModelProfile",
    "assess_compatibility",
]
