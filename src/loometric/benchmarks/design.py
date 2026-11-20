"""Strict bounded evaluation design; no performance-dependent selection."""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from loometric.benchmarks.generation import GENERATOR_VERSION, GenerationConfig
from loometric.execution import ResourceLimits as ResourceLimits
from loometric.planning.loading import fields, items, parse_json
from loometric.planning.validation import PlanningError, integer, text


@dataclass(frozen=True)
class Case:
    name: str
    tier: str
    generation: GenerationConfig


@dataclass(frozen=True)
class BenchmarkDesign:
    cases: tuple[Case, ...]
    wall_budgets_seconds: tuple[int, ...]
    deterministic_budget: float
    solver_seed: int
    repetitions: int
    resource_limits: ResourceLimits


def load_design(path: Path) -> BenchmarkDesign:
    data = fields(
        parse_json(path.read_text(encoding="utf-8")),
        (
            "schema_version",
            "generator_version",
            "seeds",
            "pressures_percent",
            "tiers",
            "wall_budgets_seconds",
            "deterministic_budget",
            "solver_seed",
            "repetitions",
            "resource_limits",
        ),
    )
    if data["schema_version"] != 1 or type(data["schema_version"]) is not int:
        raise PlanningError("INVALID_BENCHMARK", "Supported benchmark schema is 1.")
    if data["generator_version"] != GENERATOR_VERSION:
        raise PlanningError("INVALID_BENCHMARK", "Unsupported generator version.")
    integer(data["solver_seed"], "solver_seed")
    integer(data["repetitions"], "repetitions", minimum=1)
    if data["repetitions"] > 3 or data["solver_seed"] > 2**31 - 1:
        raise PlanningError("INVALID_BENCHMARK", "Unsupported repetition count/solver seed.")
    budget = data["deterministic_budget"]
    if type(budget) not in (int, Decimal) or not 0 < budget <= 10:
        raise PlanningError("INVALID_BENCHMARK", "Deterministic budget must be in (0,10].")
    lists = {}
    for name in ("seeds", "pressures_percent", "wall_budgets_seconds"):
        values = items(data[name])
        if not values or len(values) != len(set(values)):
            raise PlanningError("INVALID_BENCHMARK", f"{name} must be nonempty and unique.")
        for value in values:
            integer(value, name, minimum=0 if name == "seeds" else 1)
            if name == "wall_budgets_seconds" and value > 10:
                raise PlanningError(
                    "INVALID_BENCHMARK", "Audit phase wall budgets cannot exceed 10s."
                )
        lists[name] = values
    limits = ResourceLimits(
        **fields(data["resource_limits"], tuple(ResourceLimits.__dataclass_fields__))
    )
    cases, tier_names = [], set()
    for raw in items(data["tiers"]):
        tier = fields(
            raw,
            (
                "name",
                "orders",
                "lines",
                "stages",
                "horizon_days",
                "shifts_per_day",
                "compatible_lines",
            ),
        )
        name = tier["name"]
        text(name, "tier name")
        if not name.replace("-", "").isalnum() or name in tier_names:
            raise PlanningError("INVALID_BENCHMARK", "Tier identifiers must be unique safe names.")
        tier_names.add(name)
        for pressure in lists["pressures_percent"]:
            for seed in lists["seeds"]:
                config = GenerationConfig(
                    **{key: value for key, value in tier.items() if key != "name"},
                    target_load_percent=pressure,
                    seed=seed,
                    release_spread_days=min(1, tier["horizon_days"] - 1),
                )
                cases.append(Case(f"{name}-p{pressure}-s{seed}", name, config))
    if not cases or len(cases) * len(lists["wall_budgets_seconds"]) * data["repetitions"] > 300:
        raise PlanningError(
            "INVALID_BENCHMARK", "Matrix must contain between 1 and 300 child runs."
        )
    return BenchmarkDesign(
        tuple(cases),
        tuple(lists["wall_budgets_seconds"]),
        float(budget),
        data["solver_seed"],
        data["repetitions"],
        limits,
    )
