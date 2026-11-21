"""Trusted process-local job policy; no HTTP-controlled resource escalation."""

from importlib.resources import files

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JobLimits(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    max_active_jobs: int = Field(ge=1, le=1)
    max_waiting_jobs: int = Field(ge=0, le=2)
    max_stored_jobs: int = Field(ge=1, le=32)
    max_retained_result_bytes: int = Field(ge=1024, le=8388608)
    max_result_bytes: int = Field(ge=1024, le=2097152)
    terminal_ttl_seconds: int = Field(ge=1, le=300)
    expired_ttl_seconds: int = Field(ge=1, le=300)
    queue_timeout_seconds: int = Field(ge=1, le=30)
    wall_seconds: int = Field(ge=1, le=15)
    process_memory_mib: int = Field(ge=128, le=768)
    optimizer_memory_mib: int = Field(ge=128, le=512)
    optimizer_wall_seconds: int = Field(ge=1, le=5)
    solver_wall_seconds_per_phase: int = Field(ge=0, le=1)
    solver_deterministic_time_per_phase: int = Field(ge=0, le=1)
    max_alternatives: int = Field(ge=1, le=2000)
    max_variables: int = Field(ge=1, le=6000)
    max_constraints: int = Field(ge=1, le=15000)

    @model_validator(mode="after")
    def consistent(self) -> "JobLimits":
        if (
            self.max_result_bytes > self.max_retained_result_bytes
            or self.optimizer_memory_mib > self.process_memory_mib
            or self.optimizer_wall_seconds > self.wall_seconds
        ):
            raise ValueError("Inconsistent job resource policy.")
        return self


def default_job_limits() -> JobLimits:
    return JobLimits.model_validate_json(
        files("loometric.api").joinpath("default_job_limits.json").read_text(encoding="utf-8")
    )
