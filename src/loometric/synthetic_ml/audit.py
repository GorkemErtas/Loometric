"""Descriptive synthetic QA, without fitted preprocessing or reserved-label summaries."""

from collections import Counter, defaultdict
from decimal import Decimal, localcontext
from fractions import Fraction

from loometric.planning.domain import ARITHMETIC_CONTEXT
from loometric.synthetic_ml.configuration import GenerationConfig
from loometric.synthetic_ml.contracts import DATASET_VERSION, Dataset
from loometric.synthetic_ml.features import References, build_features, label_row
from loometric.synthetic_ml.validation import validate_dataset


def present(value: Fraction) -> Decimal:
    with localcontext(ARITHMETIC_CONTEXT):
        return Decimal(value.numerator) / Decimal(value.denominator)


def describe(values: list) -> dict:
    ordered = sorted(Fraction(value) for value in values)
    if not ordered:
        return {
            "count": 0,
            "minimum": None,
            "mean": None,
            "p50": None,
            "p95": None,
            "maximum": None,
            "unique": 0,
        }

    def quantile(q: Fraction) -> Decimal:
        location = q * (len(ordered) - 1)
        index = location.numerator // location.denominator
        weight = location - index
        return present(
            ordered[index] * (1 - weight) + ordered[min(index + 1, len(ordered) - 1)] * weight
        )

    return {
        "count": len(ordered),
        "minimum": present(ordered[0]),
        "mean": present(sum(ordered) / len(ordered)),
        "p50": quantile(Fraction(1, 2)),
        "p95": quantile(Fraction(95, 100)),
        "maximum": present(ordered[-1]),
        "unique": len(set(ordered)),
    }


def quality_report(
    data: Dataset, config: GenerationConfig, *, replay_verified: bool = False
) -> dict:
    validate_dataset(data, config)
    rows = {row["observation_id"]: row for row in build_features(data)}
    refs = References.from_dataset(data)
    plans = {p.observation_id: p for p in data.plans}
    outcomes = {o.observation_id: o for o in data.outcomes}
    groups, target_values, label_statuses = (
        defaultdict(list),
        defaultdict(list),
        defaultdict(Counter),
    )
    for member in data.membership:
        row = rows[member.observation_id]
        groups[member.partition].append(row)
        if member.partition in ("train", "validation"):
            label = label_row(plans[member.observation_id], outcomes[member.observation_id], refs)
            label_statuses[member.partition][label["status"]] += 1
            if label["standard_capacity_attainment"] is not None:
                target_values[member.partition].append(label["standard_capacity_attainment"])
    distributions, coverage = {}, {}
    train_entities = {
        key: {r["context"][key] for r in groups["train"]}
        for key in ("factory_id", "line_id", "crew_id", "style_id")
    }
    for partition, records in sorted(groups.items()):
        inputs = [r["inputs"] for r in records]
        distributions[partition] = {}
        for column in inputs[0]:
            values = [r[column] for r in inputs]
            distributions[partition][column] = (
                describe(values)
                if type(values[0]) in (int, Decimal)
                else {"counts": dict(sorted(Counter(str(v) for v in values).items()))}
            )
        coverage[partition] = {
            key: {
                "unique": len(values := {r["context"][key] for r in records}),
                "unseen_vs_train": len(values - train_entities[key]),
            }
            for key in train_entities
        }
    deltas = {}
    for partition in ("validation", "test"):
        deltas[partition] = {
            column: present(
                Fraction(summary["mean"]) - Fraction(distributions["train"][column]["mean"])
            )
            for column, summary in distributions[partition].items()
            if "mean" in summary
        }
    counts = Counter(m.partition for m in data.membership)
    test_groups = Counter(m.population for m in data.membership if m.partition == "test")
    periods = {}
    for partition, records in groups.items():
        selected = [plans[r["observation_id"]] for r in records]
        local_dates = [refs.shifts[p.shift_id].start.date() for p in selected]
        periods[partition] = {
            "first_local_start_date": min(local_dates),
            "last_local_start_date": max(local_dates),
            "observed_dates": len(set(local_dates)),
            "first_cutoff": min(p.cutoff for p in selected),
            "last_label_available_at": max(
                outcomes[p.observation_id].available_at for p in selected
            ),
        }
    population_coverage = {}
    for group in sorted(test_groups):
        selected = [
            rows[m.observation_id]
            for m in data.membership
            if m.partition == "test" and m.population == group
        ]
        population_coverage[group] = {
            key: {
                "unique": len(values := {r["context"][key] for r in selected}),
                "unseen_vs_train": len(values - train_entities[key]),
            }
            for key in train_entities
        }
    warnings = [
        f"LOW_TRAINING_VARIATION:{column}"
        for column, summary in distributions["train"].items()
        if summary.get("unique", 2) < 2
    ]
    return {
        "schema_version": 1,
        "dataset_version": DATASET_VERSION,
        "synthetic": True,
        "status": "VALID_WITH_WARNINGS" if warnings else "VALID",
        "warnings": warnings,
        "quality_score": None,
        "replay_verified": replay_verified,
        "observations": len(data.plans),
        "partitions": dict(sorted(counts.items())),
        "test_populations": dict(sorted(test_groups.items())),
        "catalog_counts": {
            name: len(getattr(data, name))
            for name in ("factories", "lines", "crews", "styles", "standards", "shifts")
        },
        "entity_coverage": coverage,
        "periods": periods,
        "test_population_entity_coverage": population_coverage,
        "feature_distributions": distributions,
        "feature_mean_delta_vs_train": deltas,
        "development_target_statistics": {
            p: {
                **describe(target_values[p]),
                "above_one": sum(v > 1 for v in target_values[p]),
                "label_statuses": dict(sorted(label_statuses[p].items())),
            }
            for p in ("train", "validation")
        },
        "reserved_test_target_statistics": "NOT_COMPUTED",
        "difficult_conditions_development_only": {
            partition: sum(
                outcomes[r["observation_id"]].difficult_condition for r in groups[partition]
            )
            for partition in ("train", "validation")
        },
        "reserved_test_policy": "INTEGRITY_AND_PHYSICAL_CHECKS_ONLY_NO_MODEL_SCORING",
        "model_training_performed": False,
        "planning_conversion_authorized": False,
        "checks": {
            key: "PASS"
            for key in (
                "schema_and_missingness",
                "references",
                "timestamps_and_cutoffs",
                "standards",
                "capacity_and_completed_piece_accounting",
                "unique_observations_and_exclusive_crews",
                "whole_date_membership",
                "label_maturity_and_embargo",
                "entity_holdouts",
                "feature_whitelist_and_availability",
                "five_stage_and_test_population_coverage",
            )
        },
        "limitations": [
            "Assumption-driven synthetic process, not measured industrial distributions.",
            "Factory/line holdouts contain nested unseen resources; not isolated effects.",
            "Independent stage orders; no material flow, rework or partial-piece credit.",
            "Target is demand-censored realized attainment; not an intrinsic efficiency parameter.",
            "Fixed offsets and Mon-Sat calendar; no DST, holidays or annual seasonality.",
        ],
    }
