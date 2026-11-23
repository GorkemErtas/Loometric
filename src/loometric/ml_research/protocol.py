"""Frozen pre-fit declaration and purged, nonoverlapping original-training windows."""

from pathlib import Path

from loometric.prediction.contracts import read_json
from loometric.synthetic_ml.storage import digest
from loometric.synthetic_training.data import Population, require
from loometric.synthetic_training.folds import Fold

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = ROOT / "configs/ml_improvement_v1.json"
SOURCE_CONFIG_SHA = "40b75e3a5854679f990cb1c6647302752ede45ed33773787172179d85c181c52"
PROTOCOL_SHA = "475da83d18ca820618520a6acfea1c6f2c6b799843f9d316ddc9b73e2d8d7591"


def load_protocol(path: Path = PROTOCOL_PATH) -> dict:
    require(path.stat().st_size <= 32768, "RESEARCH_CONFIGURATION_BYTE_LIMIT")
    config = read_json(path.read_text(encoding="utf-8"))
    # This bounded milestone has one predeclared study, not a user-configurable
    # tuning engine. A future declaration needs its own reviewed policy/version.
    require(digest(config) == PROTOCOL_SHA, "FROZEN_RESEARCH_CONFIGURATION_REQUIRED")
    require(
        config["source_study_configuration_sha256"] == SOURCE_CONFIG_SHA, "FROZEN_SOURCE_REQUIRED"
    )
    return config


def research_folds(training: Population) -> tuple[Fold, ...]:
    days = sorted(set(training.metadata.start_date))
    require(len(days) >= 18, "RESEARCH_NEEDS_EIGHTEEN_TRAINING_DATES")
    boundaries = [len(days) * fraction // 5 for fraction in (2, 3, 4, 5)]
    result, seen = [], set()
    for number, (start, stop) in enumerate(zip(boundaries[:-1], boundaries[1:], strict=True), 1):
        train_dates, evaluation_dates = days[: start - 1], days[start:stop]
        tr = tuple(training.X.index[training.metadata.start_date.isin(train_dates)])
        ev = tuple(training.X.index[training.metadata.start_date.isin(evaluation_dates)])
        require(
            bool(tr) and bool(ev) and not set(tr).intersection(ev) and not seen.intersection(ev),
            "RESEARCH_FOLD_OVERLAP_OR_EMPTY",
        )
        require(
            max(training.metadata.loc[list(tr), "label_available_at"])
            < min(training.metadata.loc[list(ev), "cutoff"]),
            "RESEARCH_LABEL_MATURITY_FAILURE",
        )
        seen.update(ev)
        result.append(
            Fold(
                f"R{number:02}",
                tr,
                ev,
                tuple(d.isoformat() for d in train_dates),
                tuple(d.isoformat() for d in evaluation_dates),
            )
        )
    return tuple(result)


def ids_fingerprint(ids) -> str:
    return digest(list(ids))
