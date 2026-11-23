"""Fixed research identities; callers cannot choose models, source paths or fit parameters."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_ROOT = ROOT / "data/processed/experimental_ml"
STUDY_DIRECTORY = ROOT / "data/processed/synthetic_training/exp-006-c"
STUDY_RECEIPT = "cd19c78c8321ac1bb69dc16d61dc7de01469e35f0d35afe3a3d8c8dca4e8b7b4"
STUDY_CASE = "benchmark-42-baseline"
VERSION = "synthetic-experimental-v1"
MODELS = {
    "random_forest": "forest-12",
    "histogram_gradient_boosting": "hist-31",
    "grouped_mean": "grouped_mean",
}
LIMITATIONS = [
    "Synthetic research only; not authorized for operational factory decisions.",
    "Demand-censored standard capacity attainment; "
    "not intrinsic employee efficiency or guaranteed output.",
    "NO_ML_PROMOTION remains unchanged; "
    "lower aggregate error does not establish stage superiority.",
    "Unseen-entity evaluation remains reserved; hidden distribution shift may be undetectable.",
    "Residual bands are descriptive, uncalibrated and have no coverage guarantee.",
    "Hypothetical input differences are not proven causal effects.",
    "No conversion to assumed_efficiency or mutation of schedules/capacity profiles.",
]
