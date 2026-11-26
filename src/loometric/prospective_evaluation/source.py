"""Outcome-free source reconstruction for EXP-009 join and seed-provenance verification."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone
from decimal import Decimal, localcontext
from fractions import Fraction

from loometric.planning.domain import ARITHMETIC_CONTEXT, Stage
from loometric.prospective_evaluation.protocol import CasePlan, load_protocol, plan_cases
from loometric.synthetic_ml.configuration import GenerationConfig
from loometric.synthetic_ml.contracts import (
    Crew,
    Dataset,
    Factory,
    Line,
    Membership,
    Order,
    Plan,
    Shift,
    Standard,
    Style,
    exact_floor,
)
from loometric.synthetic_ml.features import References, available_minutes, build_features
from loometric.synthetic_ml.generation import stream
from loometric.synthetic_ml.splitting import date_partitions, population

SOURCE_TABLES = (
    "factories",
    "lines",
    "crews",
    "styles",
    "standards",
    "shifts",
    "orders",
    "plans",
    "membership",
)
ENTITY_FIELDS = {
    "factories": ("factory", "factory_id"),
    "lines": ("line", "line_id"),
    "crews": ("crew", "crew_id"),
    "styles": ("style", "style_id"),
    "standards": ("standard", "standard_id"),
    "shifts": ("shift", "shift_id"),
    "orders": ("order", "order_id"),
}


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


@dataclass(frozen=True)
class SourceDesign:
    case: CasePlan
    configuration: GenerationConfig


def declared_designs() -> tuple[SourceDesign, ...]:
    config = load_protocol()
    parameters = {
        **config["worlds"]["parameters"],
        "start_date": date.fromisoformat(config["worlds"]["parameters"]["start_date"]),
    }
    return tuple(
        SourceDesign(case, GenerationConfig(**parameters, seed=case.seed, scenario=case.condition))
        for case in plan_cases(config)
    )


def expected_source(config: GenerationConfig) -> Dataset:
    """Independent pre-cutoff verifier of the frozen sampler, never its outcome streams.

    Deliberately reproduce only the source half of stage-shift-process-v1. This
    catches correctly rehashed seed aliases/FK edits without invoking generate or
    rebuilding latent outcomes during label-blind registration.
    """
    with localcontext(ARITHMETIC_CONTEXT):
        return _expected_source(config)


def _expected_source(config: GenerationConfig) -> Dataset:
    dates = date_partitions(config)
    reference = datetime.combine(config.start_date - timedelta(days=7), time(), UTC)
    factories = tuple(
        Factory(f"F{i:02}", (120, 180, 330)[i % 3], reference) for i in range(config.factories)
    )
    lines, crews = [], []
    for factory in factories:
        for stage in Stage:
            for i in range(config.lines_per_stage):
                line = Line(
                    f"L-{factory.factory_id}-{stage.value}-{i:02}",
                    factory.factory_id,
                    stage,
                    reference,
                )
                lines.append(line)
                for kind in ("day", "night"):
                    for cohort in ("B", "H"):
                        key = f"C-{line.line_id}-{kind}-{cohort}"
                        rng = stream(config.seed, "crew", key)
                        crews.append(
                            Crew(
                                key,
                                line.line_id,
                                kind,
                                stage,
                                rng.randint(config.workers_min, config.workers_max),
                                rng.randint(1, 5),
                                reference,
                            )
                        )
    styles = tuple(
        Style(f"S{i:02}", stream(config.seed, "style", str(i)).randint(1, 5), reference)
        for i in range(config.styles)
    )
    standards = tuple(
        Standard(
            f"STD-{style.style_id}-{stage.value}",
            style.style_id,
            stage,
            Decimal(
                stream(config.seed, "standard", f"{style.style_id}|{stage.value}").randint(
                    config.standard_hundredths_min
                    + (config.standard_hundredths_max - config.standard_hundredths_min)
                    * (style.complexity - 1)
                    // 8,
                    config.standard_hundredths_min
                    + (config.standard_hundredths_max - config.standard_hundredths_min)
                    * (style.complexity + 3)
                    // 8,
                )
            )
            / Decimal(100),
            reference,
        )
        for style in styles
        for stage in Stage
    )
    standards_by_key = {(s.style_id, s.stage): s for s in standards}
    crews_by_id = {c.crew_id: c for c in crews}
    shifts, orders, plans, membership = [], [], [], []
    future = [day for day, part in dates.items() if part == "test"]
    for day, partition in dates.items():
        test_index = future.index(day) if partition == "test" else -1
        for factory in factories:
            for kind, hour in (("day", 8), ("night", 20)):
                if partition != "test" and factory == factories[-1]:
                    continue
                start = datetime.combine(
                    day, time(hour), timezone(timedelta(minutes=factory.utc_offset_minutes))
                )
                shift = Shift(
                    f"SH-{factory.factory_id}-{day.isoformat()}-{kind}",
                    factory.factory_id,
                    kind,
                    start,
                    start + timedelta(hours=8),
                    start + timedelta(hours=4),
                    start + timedelta(hours=4, minutes=30),
                    start - timedelta(days=1),
                )
                shifts.append(shift)
                for line in (v for v in lines if v.factory_id == factory.factory_id):
                    if partition != "test" and line.line_id.endswith(
                        f"-{config.lines_per_stage - 1:02}"
                    ):
                        continue
                    cohort = "H" if partition == "test" and test_index % 3 == 1 else "B"
                    crew = crews_by_id[f"C-{line.line_id}-{kind}-{cohort}"]
                    oid = f"OBS-{shift.shift_id}-{line.line_id}"
                    rng = stream(config.seed, "plan", oid)
                    style = (
                        styles[-1]
                        if partition == "test" and test_index % 3 == 2
                        else (styles[rng.randrange(len(styles) - 1)])
                    )
                    standard = standards_by_key[style.style_id, line.stage]
                    cutoff = start - timedelta(minutes=30)
                    workers = rng.randint(max(1, crew.roster_size - 2), crew.roster_size)
                    stop, machine = (
                        rng.randint(0, config.planned_downtime_max),
                        rng.randrange(100) != 0,
                    )
                    plan = Plan(
                        oid,
                        line.line_id,
                        crew.crew_id,
                        shift.shift_id,
                        f"O-{oid}",
                        standard.standard_id,
                        workers,
                        machine,
                        start + timedelta(minutes=90),
                        start + timedelta(minutes=90 + stop),
                        0,
                        0,
                        cutoff - timedelta(minutes=5),
                        cutoff,
                    )
                    # Exercise the same unioned break/stop accounting, without a label join.
                    available_minutes(plan, shift)
                    load = rng.randint(config.workload_percent_min, config.workload_percent_max)
                    if config.scenario == "workload_surge" and partition not in ("train", "gap"):
                        load = load * 3 // 2
                    quantity = max(
                        1,
                        exact_floor(
                            Fraction(450 * workers * load, 100)
                            / Fraction(standard.worker_minutes_per_piece)
                        ),
                    )
                    opening = rng.randint(0, quantity)
                    plan = Plan(
                        **{
                            **vars(plan),
                            "opening_wip_pieces": opening,
                            "planned_release_pieces": quantity - opening,
                        }
                    )
                    orders.append(
                        Order(plan.order_id, style.style_id, quantity, cutoff - timedelta(hours=1))
                    )
                    plans.append(plan)
                    membership.append(
                        Membership(
                            oid,
                            partition,
                            population(
                                factory.factory_id,
                                line.line_id,
                                crew.crew_id,
                                style.style_id,
                                config,
                            )
                            if partition == "test"
                            else "familiar",
                        )
                    )
    return Dataset(
        factories,
        tuple(lines),
        tuple(crews),
        styles,
        standards,
        tuple(shifts),
        tuple(orders),
        tuple(plans),
        (),
        tuple(membership),
    )


def audit_source(data: Dataset, design: SourceDesign) -> tuple[dict, ...]:
    """Actual source joins, exact exposure grid, and temporal checks, without targets."""
    require(
        design.case.seed == design.configuration.seed
        and design.case.condition == design.configuration.scenario,
        "CASE_CONFIGURATION_IDENTITY_DRIFT",
    )
    expected = expected_source(design.configuration)
    require(
        all(getattr(data, name) == getattr(expected, name) for name in SOURCE_TABLES),
        "SOURCE_JOIN_OR_SEED_PROVENANCE_DRIFT",
    )
    refs = References.from_dataset(data)
    factories = {f.factory_id: f for f in data.factories}
    rows = build_features(data)
    selected = {m.observation_id for m in data.membership if m.partition == "validation"}
    require(
        len(data.plans) == design.case.source_rows and len(selected) == design.case.planned_rows,
        "EXACT_CASE_EXPOSURE_REQUIRED",
    )
    observed_dates = set()
    for plan in data.plans:
        shift = refs.shifts[plan.shift_id]
        factory = factories[refs.lines[plan.line_id].factory_id]
        require(
            factory.available_at <= plan.cutoff
            and plan.snapshot_at == plan.cutoff - timedelta(minutes=5),
            "LATE_SOURCE_OR_SNAPSHOT",
        )
        if plan.observation_id in selected:
            require(plan.cutoff > datetime(2031, 1, 8, tzinfo=UTC), "HISTORICAL_TEMPORAL_OVERLAP")
            observed_dates.add(shift.start.date())
    require(observed_dates == set(design.case.score_dates), "EXACT_SCORE_CALENDAR_REQUIRED")
    return rows


def scoped_entities(data: Dataset, world_id: str) -> tuple[dict, ...]:
    return tuple(
        {"kind": kind, "world_id": world_id, "local_id": getattr(row, field)}
        for table, (kind, field) in ENTITY_FIELDS.items()
        for row in getattr(data, table)
    )
