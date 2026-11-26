"""Declared raw-population diagnostics. No model selection, clipping or calibration."""

import hashlib
import random
from collections import Counter
from fractions import Fraction
from itertools import combinations, product
from math import fsum, isfinite, sqrt

import numpy as np

from loometric.planning.domain import Stage
from loometric.prospective_evaluation.source import require
from loometric.prospective_evaluation.storage import encode, sha256

METRICS = (
    "mae",
    "rmse",
    "r2",
    "bias",
    "p95_absolute_error",
    "worst_absolute_error",
    "p95_positive_error",
)
STATUSES = ("SUPPORTED_EXPERIMENTAL", "REVIEW_REQUIRED", "ABSTAIN")


def mean(values):
    return fsum(values) / len(values) if values else None


def quantile(values, q):
    return float(np.quantile(values, q, method="linear")) if len(values) else None


def metrics(rows: list[dict], model: str) -> dict:
    selected = [r for r in rows if r["actual"] is not None]
    if not selected:
        return {"rows": 0, **dict.fromkeys(METRICS)}
    actual = [r["actual"] for r in selected]
    predictions = [r["predictions"][model] for r in selected]
    require(all(isfinite(v) for v in actual + predictions), "NONFINITE_EVALUATION_VALUE")
    residual = [p - y for y, p in zip(actual, predictions, strict=True)]
    errors = [abs(r) for r in residual]
    center = mean(actual)
    total = fsum((y - center) ** 2 for y in actual)
    squared = fsum(r * r for r in residual)
    return {
        "rows": len(actual),
        "mae": mean(errors),
        "rmse": sqrt(squared / len(actual)),
        "r2": 1 - squared / total if len(actual) >= 2 and total else None,
        "bias": mean(residual),
        "p95_absolute_error": quantile(errors, 0.95),
        "worst_absolute_error": max(errors),
        "p95_positive_error": quantile([max(r, 0) for r in residual], 0.95),
    }


def counts(rows):
    return {
        "rows": len(rows),
        **{
            plural: len({r[key] for r in rows})
            for plural, key in (
                ("dates", "date"),
                ("factories", "factory"),
                ("lines", "line"),
                ("crews", "crew"),
                ("styles", "style"),
            )
        },
    }


def cell(rows, model):
    valid = [r for r in rows if r["actual"] is not None]
    return {
        "planned_counts": counts(rows),
        "defined_target_counts": counts(valid),
        "low_support": len(valid) < 30,
        "metrics": metrics(valid, model),
    }


def band(value, a, b):
    return "low" if value <= a else "nominal" if value <= b else "high"


def subgroup_key(row, group, model):
    inputs = row["inputs"]
    if group == "staffing_band":
        return {"low": "1-5", "nominal": "6-10", "high": "11+"}[
            band(inputs["planned_workers"], 5, 10)
        ]
    if group == "workload_band":
        return (
            band(Fraction(row["offered_ceiling"]), Fraction(3, 5), Fraction(1))
            if row["offered_ceiling"] is not None
            else "undefined_zero_capacity"
        )
    if group == "interruption_band":
        return {"low": "0", "nominal": "1-30", "high": "31+"}[
            band(inputs["planned_downtime_minutes"], 0, 30)
        ]
    if group == "support_status":
        return row["support"][model]["status"]
    return row[group]


def case_diagnostics(rows, models, config):
    report = {}
    domains = {
        "stage": [s.value for s in Stage],
        "shift_kind": ["day", "night"],
        "staffing_band": ["1-5", "6-10", "11+"],
        "workload_band": ["low", "nominal", "high", "undefined_zero_capacity"],
        "interruption_band": ["0", "1-30", "31+"],
        "support_status": STATUSES,
    }
    for model in models:
        valid = [r for r in rows if r["actual"] is not None]
        subgroups = {}
        for group in config["evaluation"]["subgroups"]:
            keys = domains.get(group, sorted({subgroup_key(r, group, model) for r in rows}))
            subgroups[group] = {
                key: cell([r for r in rows if subgroup_key(r, group, model) == key], model)
                for key in keys
            }
        support = {}
        for population, selected in (("all_planned", rows), ("defined_targets", valid)):
            n = len(selected)
            input_abstain = sum(r["input_support"]["status"] == "ABSTAIN" for r in selected)
            final_abstain = sum(r["support"][model]["status"] == "ABSTAIN" for r in selected)
            output_abstain = sum(
                r["input_support"]["status"] != "ABSTAIN"
                and r["support"][model]["status"] == "ABSTAIN"
                for r in selected
            )
            support[population] = {
                "denominator": n,
                "input_status_counts": dict(
                    Counter(r["input_support"]["status"] for r in selected)
                ),
                "status_counts": {
                    s: sum(r["support"][model]["status"] == s for r in selected) for s in STATUSES
                },
                "input_reason_counts": dict(
                    Counter(c for r in selected for c in r["input_support"]["reason_codes"])
                ),
                "reason_counts": dict(
                    Counter(c for r in selected for c in r["support"][model]["reason_codes"])
                ),
                "input_abstentions": input_abstain,
                "output_added_abstentions": output_abstain,
                "abstentions": final_abstain,
                "input_abstention_rate": input_abstain / n if n else None,
                "output_added_abstention_rate": output_abstain / n if n else None,
                "abstention_rate": final_abstain / n if n else None,
                "coverage_rate": (n - final_abstain) / n if n else None,
                "input_coverage_rate": (n - input_abstain) / n if n else None,
            }
        predictions = [r["predictions"][model] for r in valid]
        worst = sorted(valid, key=lambda r: (-abs(r["predictions"][model] - r["actual"]), r["id"]))[
            :10
        ]
        report[model] = {
            **cell(rows, model),
            "subgroups": subgroups,
            "support": support,
            "raw_output": {
                "minimum": min(predictions, default=None),
                "maximum": max(predictions, default=None),
                "below_zero": sum(p < 0 for p in predictions),
                "above_one": sum(p > 1 for p in predictions),
                "above_three": sum(p > 3 for p in predictions),
                "above_offered_work_ceiling": sum(
                    r["predictions"][model] > float(Fraction(r["offered_ceiling"])) for r in valid
                ),
            },
            "worst_observations": [
                {
                    "id": r["id"],
                    "actual": r["actual"],
                    "prediction": r["predictions"][model],
                    "absolute_error": abs(r["predictions"][model] - r["actual"]),
                }
                for r in worst
            ],
        }
    common = [
        r
        for r in rows
        if r["actual"] is not None and all(r["support"][m]["status"] != "ABSTAIN" for m in models)
    ]
    return {
        "models": report,
        "common_nonabstained_secondary": {
            "ids": [r["id"] for r in common],
            "metrics": {m: metrics(common, m) for m in models},
        },
    }


def difference(left, right):
    return {
        m: left[m] - right[m] if left[m] is not None and right[m] is not None else None
        for m in METRICS
    }


def macro(values):
    return {
        m: mean([v[m] for v in values]) if all(v[m] is not None for v in values) else None
        for m in METRICS
    }


def bootstrap_interval(values):
    """All ordered 4^4 paired world draws, equal weights, never row bootstrap."""
    require(len(values) == 4, "FOUR_WORLD_BLOCKS_REQUIRED")
    if any(v is None for v in values):
        return {"ordered_resamples": 256, "interval": [None, None], "resamples_sha256": None}
    draws = [mean([values[i] for i in indices]) for indices in product(range(4), repeat=4)]
    return {
        "ordered_resamples": len(draws),
        "interval": [quantile(draws, 0.025), quantile(draws, 0.975)],
        "resamples_sha256": sha256(encode(draws)),
    }


def comparisons(cases, designs, models):
    pairs = list(combinations(models, 2))
    worlds = sorted({d.case.world_id for d in designs})
    indexed = {(d.case.world_id, d.case.condition): cases[d.case.case_id] for d in designs}
    output = {"model_pairs": {}, "condition_changes": {}, "identical_input_mae_floor": {}}
    for condition in ("baseline", "disruption"):
        output["model_pairs"][condition] = {}
        for left, right in pairs:
            individual = {
                w: difference(
                    metrics(indexed[w, condition], left), metrics(indexed[w, condition], right)
                )
                for w in worlds
            }
            output["model_pairs"][condition][f"{left}_minus_{right}"] = {
                "individual_worlds": individual,
                "macro": macro(list(individual.values())),
                "world_bootstrap": bootstrap_interval([individual[w]["mae"] for w in worlds]),
            }
    for world in worlds:
        baseline, disrupted = indexed[world, "baseline"], indexed[world, "disruption"]
        require(
            [r["id"] for r in baseline] == [r["id"] for r in disrupted], "PAIRED_SCORE_IDS_DRIFT"
        )
        matched = [
            (a, b)
            for a, b in zip(baseline, disrupted, strict=True)
            if a["actual"] is not None and b["actual"] is not None
        ]
        require(
            sum(r["actual"] is not None for r in baseline)
            == len(matched)
            == sum(r["actual"] is not None for r in disrupted),
            "PAIRED_TARGET_POPULATION_DRIFT",
        )
        output["identical_input_mae_floor"][world] = mean(
            [abs(a["actual"] - b["actual"]) / 2 for a, b in matched]
        )
        output["condition_changes"][world] = {
            m: difference(metrics(disrupted, m), metrics(baseline, m)) for m in models
        }
    output["condition_changes_macro"] = {
        m: macro([output["condition_changes"][w][m] for w in worlds]) for m in models
    }
    output["condition_world_bootstrap"] = {
        m: bootstrap_interval([output["condition_changes"][w][m]["mae"] for w in worlds])
        for m in models
    }
    output["identical_input_mae_floor_macro"] = (
        mean(list(output["identical_input_mae_floor"].values()))
        if all(v is not None for v in output["identical_input_mae_floor"].values())
        else None
    )
    primary = [metrics(indexed[w, "baseline"], "rf_physics")["mae"] for w in worlds]
    forest = [metrics(indexed[w, "baseline"], "random_forest")["mae"] for w in worlds]
    contrast = [
        a - b if a is not None and b is not None else None
        for a, b in zip(primary, forest, strict=True)
    ]
    output["primary"] = {
        "left": "rf_physics",
        "right": "random_forest",
        "condition": "baseline",
        "individual_worlds": dict(zip(worlds, contrast, strict=True)),
        **bootstrap_interval(contrast),
    }
    return output


def date_sensitivity(cases, designs, models, config):
    """All models/conditions share each draw of complete local start-date blocks."""
    result = {}
    for world in sorted({d.case.world_id for d in designs}):
        by_condition = {
            d.case.condition: cases[d.case.case_id] for d in designs if d.case.world_id == world
        }
        dates = sorted({r["date"] for r in by_condition["baseline"]})
        require(
            dates == sorted({r["date"] for r in by_condition["disruption"]}),
            "PAIRED_DATE_BLOCK_DRIFT",
        )
        # Preaggregate absolute residual sums/counts by whole date. No row resampling.
        blocks = {
            (c, m, date): (
                fsum(
                    abs(r["predictions"][m] - r["actual"])
                    for r in rows
                    if r["date"] == date and r["actual"] is not None
                ),
                sum(r["date"] == date and r["actual"] is not None for r in rows),
            )
            for c, rows in by_condition.items()
            for m in models
            for date in dates
        }
        samples = {
            f"{c}|{a}_minus_{b}": [] for c in by_condition for a, b in combinations(models, 2)
        }
        samples.update({f"disruption_minus_baseline|{m}": [] for m in models})
        draws = []
        for replicate in range(config["uncertainty"]["sensitivity"]["repeats"]):
            key = config["uncertainty"]["sensitivity"]["key_template"].format(
                world_id=world, replicate=replicate
            )
            rng = random.Random(int.from_bytes(hashlib.sha256(key.encode()).digest(), "big"))
            draw = [rng.choice(dates) for _ in dates]
            draws.append(draw)
            averages = {}
            for c in by_condition:
                for m in models:
                    total = sum(blocks[c, m, d][1] for d in draw)
                    averages[c, m] = (
                        fsum(blocks[c, m, d][0] for d in draw) / total if total else None
                    )
            for c in by_condition:
                for a, b in combinations(models, 2):
                    left, right = averages[c, a], averages[c, b]
                    samples[f"{c}|{a}_minus_{b}"].append(
                        left - right if left is not None and right is not None else None
                    )
            for m in models:
                left, right = averages["disruption", m], averages["baseline", m]
                samples[f"disruption_minus_baseline|{m}"].append(
                    left - right if left is not None and right is not None else None
                )
        result[world] = {
            "repeats": len(draws),
            "dates_per_draw": len(dates),
            "draws_sha256": sha256(encode(draws)),
            "used_for_acceptance": False,
            "contrasts": {
                name: {
                    "undefined_draws": values.count(None),
                    "interval": [quantile(values, 0.025), quantile(values, 0.975)]
                    if None not in values
                    else [None, None],
                    "resamples_sha256": sha256(encode(values)),
                }
                for name, values in samples.items()
            },
        }
    return result
