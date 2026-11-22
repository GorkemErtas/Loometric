"""Seeded independent stage-shift process, never fitted to historical data."""

import hashlib
import random
from datetime import UTC, datetime, time, timedelta, timezone
from decimal import Decimal, localcontext
from fractions import Fraction

from loometric.planning.domain import ARITHMETIC_CONTEXT, Stage
from loometric.synthetic_ml.configuration import GenerationConfig
from loometric.synthetic_ml.contracts import (
    Crew,
    Dataset,
    Factory,
    Line,
    Membership,
    Order,
    Outcome,
    Plan,
    Shift,
    Standard,
    Style,
    exact_floor,
)
from loometric.synthetic_ml.features import available_minutes
from loometric.synthetic_ml.splitting import date_partitions, population


def stream(seed: int, kind: str, key: str) -> random.Random:
    """Independent content-keyed streams; no global RNG and no outcome feedback."""
    digest = hashlib.sha256(f"stage-shift-process-v1|{seed}|{kind}|{key}".encode()).digest()
    return random.Random(int.from_bytes(digest, "big"))


def _generate(config: GenerationConfig) -> Dataset:
    dates = date_partitions(config)
    reference_time = datetime.combine(config.start_date - timedelta(days=7), time(), UTC)
    factories = tuple(
        Factory(f"F{i:02}", (120, 180, 330)[i % 3], reference_time) for i in range(config.factories)
    )
    lines, crews = [], []
    for factory in factories:
        for stage in Stage:
            for i in range(config.lines_per_stage):
                line = Line(
                    f"L-{factory.factory_id}-{stage.value}-{i:02}",
                    factory.factory_id,
                    stage,
                    reference_time,
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
                                reference_time,
                            )
                        )
    styles = tuple(
        Style(f"S{i:02}", stream(config.seed, "style", str(i)).randint(1, 5), reference_time)
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
            reference_time,
        )
        for style in styles
        for stage in Stage
    )
    standard_map = {(s.style_id, s.stage): s for s in standards}
    crew_map = {c.crew_id: c for c in crews}
    line_rates = {
        line.line_id: stream(config.seed, "latent_line", line.line_id).randint(7500, 12500)
        for line in lines
    }
    crew_rates = {
        crew.crew_id: stream(config.seed, "latent_crew", crew.crew_id).randint(8500, 11500)
        for crew in crews
    }
    shifts, orders, plans, outcomes, membership = [], [], [], [], []
    future_dates = [day for day, partition in dates.items() if partition == "test"]
    for day, partition in dates.items():
        test_index = future_dates.index(day) if partition == "test" else -1
        for factory in factories:
            zone = timezone(timedelta(minutes=factory.utc_offset_minutes))
            for kind, hour in (("day", 8), ("night", 20)):
                start = datetime.combine(day, time(hour), zone)
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
                # No held-out factory or line observations before the future test period.
                if partition != "test" and factory == factories[-1]:
                    continue
                shifts.append(shift)
                for line in (line for line in lines if line.factory_id == factory.factory_id):
                    if partition != "test" and line.line_id.endswith(
                        f"-{config.lines_per_stage - 1:02}"
                    ):
                        continue
                    cohort = "H" if partition == "test" and test_index % 3 == 1 else "B"
                    crew = crew_map[f"C-{line.line_id}-{kind}-{cohort}"]
                    oid = f"OBS-{shift.shift_id}-{line.line_id}"
                    rng = stream(config.seed, "plan", oid)
                    style = (
                        styles[-1]
                        if partition == "test" and test_index % 3 == 2
                        else styles[rng.randrange(len(styles) - 1)]
                    )
                    standard = standard_map[style.style_id, line.stage]
                    cutoff = start - timedelta(minutes=30)
                    workers = rng.randint(max(1, crew.roster_size - 2), crew.roster_size)
                    stop = rng.randint(0, config.planned_downtime_max)
                    machine = rng.randrange(100) != 0
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
                    minutes = available_minutes(plan, shift)
                    load = rng.randint(config.workload_percent_min, config.workload_percent_max)
                    if config.scenario == "workload_surge" and partition not in ("train", "gap"):
                        load = load * 3 // 2
                    # Workload is planned without reading sampled outcomes or latent process rates.
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
                            **plan.__dict__,
                            "opening_wip_pieces": opening,
                            "planned_release_pieces": quantity - opening,
                        }
                    )
                    orders.append(
                        Order(plan.order_id, style.style_id, quantity, cutoff - timedelta(hours=1))
                    )
                    outcome_rng = stream(config.seed, "outcome", oid)
                    difficult = outcome_rng.randrange(1000) < config.difficult_per_thousand
                    absent = min(
                        workers,
                        int(outcome_rng.randrange(100) < 12) + int(outcome_rng.randrange(100) < 3),
                    )
                    realized = workers - absent
                    loss = outcome_rng.randint(0, min(minutes, 35)) if minutes else 0
                    if difficult:
                        loss = min(minutes, loss + outcome_rng.randint(40, 120))
                    noise = (
                        sum(
                            outcome_rng.randint(-config.process_noise_bps, config.process_noise_bps)
                            for _ in range(6)
                        )
                        // 6
                    )
                    rate = Fraction(line_rates[line.line_id], 10000) * Fraction(
                        crew_rates[crew.crew_id], 10000
                    )
                    rate *= Fraction(
                        stream(config.seed, "latent_shift", shift.shift_id).randint(9500, 10500),
                        10000,
                    )
                    rate *= Fraction(8000 + 600 * crew.skill_level, 10000)
                    rate *= Fraction(11000 - 200 * style.complexity, 10000)
                    rate *= Fraction(9300 if kind == "night" else 10000, 10000)
                    rate *= Fraction(10000 + noise, 10000)
                    if difficult:
                        rate *= Fraction(65, 100)
                    if config.scenario == "disruption" and partition not in ("train", "gap"):
                        loss = min(minutes, loss + 60)
                        rate *= Fraction(80, 100)
                    possible = exact_floor(
                        Fraction((minutes - loss) * realized)
                        * rate
                        / Fraction(standard.worker_minutes_per_piece)
                    )
                    completed = min(quantity, possible)
                    outcomes.append(
                        Outcome(
                            oid,
                            realized,
                            loss,
                            difficult,
                            completed,
                            quantity - completed,
                            shift.end + timedelta(minutes=config.label_delay_minutes),
                        )
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
        tuple(outcomes),
        tuple(membership),
    )


def generate(config: GenerationConfig) -> Dataset:
    """Decimal arithmetic is isolated from the caller's mutable precision context."""
    if not isinstance(config, GenerationConfig):
        raise TypeError("Typed synthetic generation configuration required.")
    with localcontext(ARITHMETIC_CONTEXT):
        return _generate(config)
