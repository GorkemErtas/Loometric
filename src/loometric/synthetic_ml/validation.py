"""Independent schema, foreign-key, calendar, accounting and holdout checks."""

from collections import Counter, defaultdict
from dataclasses import fields
from datetime import datetime, timedelta
from decimal import Decimal
from fractions import Fraction

from loometric.planning.domain import Stage
from loometric.synthetic_ml.configuration import GenerationConfig
from loometric.synthetic_ml.contracts import TABLE_TYPES, Dataset
from loometric.synthetic_ml.features import (
    FEATURE_COLUMNS,
    References,
    available_minutes,
    feature_row,
)
from loometric.synthetic_ml.splitting import TEST_POPULATIONS, date_partitions, population

KEYS = {name: next(iter(cls.__dataclass_fields__)) for name, cls in TABLE_TYPES.items()}


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def _index(data: Dataset) -> dict[str, dict]:
    indexes = {}
    for name, cls in TABLE_TYPES.items():
        records = getattr(data, name)
        require(type(records) is tuple and bool(records), f"MISSING_TABLE:{name}")
        index = {}
        for record in records:
            require(type(record) is cls, f"INVALID_RECORD:{name}")
            for field in fields(cls):
                value = getattr(record, field.name)
                require(type(value) is field.type, f"INVALID_TYPE:{name}.{field.name}")
                if field.type is int:
                    require(value >= 0, f"NEGATIVE_VALUE:{name}.{field.name}")
                elif field.type is str:
                    require(
                        bool(value)
                        and value == value.strip()
                        and len(value) <= 200
                        and all(ord(c) >= 32 for c in value),
                        f"INVALID_ID:{name}.{field.name}",
                    )
                elif field.type is Decimal:
                    require(
                        value.is_finite() and value > 0 and value.as_tuple().exponent >= -2,
                        f"INVALID_STANDARD:{name}.{field.name}",
                    )
                elif field.type is datetime:
                    require(
                        value.tzinfo is not None
                        and value.utcoffset() is not None
                        and value.second == value.microsecond == 0,
                        f"INVALID_TIMESTAMP:{name}.{field.name}",
                    )
            key = getattr(record, KEYS[name])
            require(key not in index, f"DUPLICATE_KEY:{name}")
            index[key] = record
        indexes[name] = index
    return indexes


def validate_dataset(data: Dataset, config: GenerationConfig) -> None:
    """Fail explicitly; no dropping, coercing, clipping, repairing or imputation."""
    require(type(data) is Dataset and type(config) is GenerationConfig, "TYPED_DATASET_REQUIRED")
    indexes = _index(data)
    factories, lines, crews = (indexes[n] for n in ("factories", "lines", "crews"))
    shifts, orders, standards = (indexes[n] for n in ("shifts", "orders", "standards"))
    require(
        len(factories) == config.factories
        and len(lines) == config.factories * 5 * config.lines_per_stage
        and len(crews) == len(lines) * 4
        and len(indexes["styles"]) == config.styles
        and len(standards) == config.styles * 5,
        "CATALOG_COVERAGE",
    )
    for factory in factories.values():
        require(factory.utc_offset_minutes in (120, 180, 330), "FACTORY_OFFSET")
    for line in lines.values():
        require(line.factory_id in factories, "LINE_FACTORY_REFERENCE")
    for crew in crews.values():
        require(
            crew.line_id in lines and crew.qualified_stage == lines[crew.line_id].stage,
            "CREW_QUALIFICATION_REFERENCE",
        )
        require(
            crew.shift_kind in ("day", "night")
            and config.workers_min <= crew.roster_size <= config.workers_max
            and 1 <= crew.skill_level <= 5,
            "CREW_DEFINITION",
        )
    standard_pairs = set()
    for standard in standards.values():
        require(standard.style_id in indexes["styles"], "STANDARD_STYLE_REFERENCE")
        require((standard.style_id, standard.stage) not in standard_pairs, "DUPLICATE_STYLE_STAGE")
        standard_pairs.add((standard.style_id, standard.stage))
    require(
        standard_pairs == {(s, stage) for s in indexes["styles"] for stage in Stage},
        "STANDARD_COVERAGE",
    )
    require(all(1 <= s.complexity <= 5 for s in data.styles), "STYLE_COMPLEXITY")
    for order in orders.values():
        require(order.style_id in indexes["styles"] and order.quantity > 0, "ORDER_REFERENCE")
    dates = date_partitions(config)
    for shift in shifts.values():
        require(shift.factory_id in factories and shift.kind in ("day", "night"), "SHIFT_REFERENCE")
        require(
            all(
                t.utcoffset() == timedelta(minutes=factories[shift.factory_id].utc_offset_minutes)
                for t in (shift.start, shift.end, shift.break_start, shift.break_end)
            ),
            "SHIFT_CALENDAR_OFFSET",
        )
        require(
            shift.end - shift.start == timedelta(hours=8)
            and shift.start.hour == (8 if shift.kind == "day" else 20)
            and shift.start.minute == 0
            and shift.start.date() in dates,
            "SHIFT_CALENDAR",
        )
        require(
            shift.start <= shift.break_start < shift.break_end <= shift.end
            and shift.break_end - shift.break_start == timedelta(minutes=30),
            "SHIFT_BREAK",
        )
    ids = set(indexes["plans"])
    require(
        all(set(indexes[n]) == ids for n in ("outcomes", "membership")) and len(orders) == len(ids),
        "OBSERVATION_COVERAGE",
    )
    refs = References.from_dataset(data)
    line_slots, crew_slots, grain, order_ids = defaultdict(list), defaultdict(list), set(), set()
    partition_cutoffs, partition_labels = defaultdict(list), defaultdict(list)
    counts, stages, populations = Counter(), defaultdict(set), set()
    for plan in data.plans:
        require(
            plan.line_id in lines
            and plan.crew_id in crews
            and plan.shift_id in shifts
            and plan.order_id in orders
            and plan.standard_id in standards,
            "PLAN_FOREIGN_KEY",
        )
        line, crew, shift = lines[plan.line_id], crews[plan.crew_id], shifts[plan.shift_id]
        order, standard = orders[plan.order_id], standards[plan.standard_id]
        require(
            line.factory_id == shift.factory_id
            and crew.line_id == line.line_id
            and crew.shift_kind == shift.kind
            and crew.qualified_stage == standard.stage == line.stage
            and standard.style_id == order.style_id,
            "PLAN_PROCESS_CREW_STYLE",
        )
        require(
            plan.planned_workers <= crew.roster_size
            and plan.cutoff == shift.start - timedelta(minutes=30)
            and factories[line.factory_id].available_at <= plan.cutoff,
            "PLAN_STAFFING_OR_CUTOFF",
        )
        require(
            shift.start <= plan.downtime_start <= plan.downtime_end <= shift.end,
            "PLANNED_DOWNTIME_INTERVAL",
        )
        require(
            plan.opening_wip_pieces + plan.planned_release_pieces == order.quantity,
            "WORKLOAD_BALANCE",
        )
        require(plan.order_id not in order_ids, "ORDER_REUSED_ACROSS_OBSERVATIONS")
        order_ids.add(plan.order_id)
        key = (plan.line_id, plan.crew_id, plan.shift_id, plan.order_id)
        require(key not in grain, "DUPLICATE_OBSERVATION")
        grain.add(key)
        row = feature_row(plan, refs)  # Includes pre-cutoff availability of every joined source.
        require(set(row["inputs"]) == set(FEATURE_COLUMNS), "FEATURE_WHITELIST")
        minutes = available_minutes(plan, shift)
        outcome = indexes["outcomes"][plan.observation_id]
        require(
            outcome.realized_workers <= plan.planned_workers
            and outcome.unplanned_loss_minutes <= minutes
            and outcome.available_at == shift.end + timedelta(minutes=config.label_delay_minutes),
            "OUTCOME_STAFFING_TIMING_LOSS",
        )
        require(
            outcome.completed_good_pieces + outcome.closing_wip_pieces == order.quantity,
            "PRODUCTION_BALANCE",
        )
        actual_labor = (minutes - outcome.unplanned_loss_minutes) * outcome.realized_workers
        require(
            Fraction(outcome.completed_good_pieces) * Fraction(standard.worker_minutes_per_piece)
            <= actual_labor * 3,
            "PHYSICAL_RATE_ENVELOPE",
        )
        member = indexes["membership"][plan.observation_id]
        require(member.partition == dates[shift.start.date()], "CHRONOLOGICAL_MEMBERSHIP")
        expected = population(line.factory_id, line.line_id, crew.crew_id, order.style_id, config)
        if member.partition == "test":
            require(member.population == expected, "TEST_POPULATION")
            populations.add(expected)
        else:
            require(
                member.population == "familiar" and expected == "future_familiar",
                "HELDOUT_ENTITY_IN_DEVELOPMENT",
            )
        counts[shift.start.date()] += 1
        stages[member.partition].add(line.stage)
        line_slots[line.line_id].append((shift.start, shift.end))
        crew_slots[crew.crew_id].append((shift.start, shift.end))
        partition_cutoffs[member.partition].append(plan.cutoff)
        partition_labels[member.partition].append(outcome.available_at)
    for slots in (*line_slots.values(), *crew_slots.values()):
        ordered = sorted(slots)
        require(
            all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:], strict=False)),
            "OVERLAPPING_RESOURCE",
        )
    for day, part in dates.items():
        expected_count = (
            (
                config.factories * config.lines_per_stage
                if part == "test"
                else (config.factories - 1) * (config.lines_per_stage - 1)
            )
            * 5
            * 2
        )
        require(counts[day] == expected_count, "EXPOSURE_COVERAGE")
    require(populations == set(TEST_POPULATIONS), "GENERALIZATION_COVERAGE")
    require(all(stages[p] == set(Stage) for p in ("train", "validation", "test")), "STAGE_COVERAGE")
    for earlier, later in (("train", "validation"), ("validation", "test")):
        require(
            max(partition_labels[earlier]) < min(partition_cutoffs[later]),
            "LABEL_AVAILABILITY_REQUIRES_LONGER_EMBARGO",
        )
