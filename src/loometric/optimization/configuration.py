"""Explicit solver budgets and deterministic benchmark configuration."""

from dataclasses import dataclass
from math import isfinite

from loometric.planning.validation import PlanningError, integer


@dataclass(frozen=True)
class SolverConfiguration:
    random_seed: int = 42
    workers: int = 1
    wall_time_seconds_per_phase: float = 10.0
    deterministic_time_per_phase: float = 1.0
    benchmark_mode: bool = True

    def __post_init__(self) -> None:
        integer(self.random_seed, "random_seed")
        integer(self.workers, "workers", minimum=1)
        if self.random_seed > 2**31 - 1 or self.workers > 2**31 - 1:
            raise PlanningError(
                "INVALID_SOLVER_CONFIGURATION", "Seed/workers must fit positive int32 parameters."
            )
        for name in ("wall_time_seconds_per_phase", "deterministic_time_per_phase"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not isfinite(value) or value < 0:
                raise PlanningError(
                    "INVALID_SOLVER_CONFIGURATION", f"{name} must be finite and nonnegative."
                )
        if type(self.benchmark_mode) is not bool or (self.benchmark_mode and self.workers != 1):
            raise PlanningError(
                "INVALID_SOLVER_CONFIGURATION", "Benchmark mode requires exactly one worker."
            )
