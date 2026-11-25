"""Fixed identities for experimental research model publication."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

VERSION = "synthetic-experimental-v2"
MODEL_NAME = "rf_physics"
MODEL_STATUS = "RESEARCH_CANDIDATE"

SOURCE_EXPERIMENT = "EXP-008"

SOURCE_DIRECTORY = ROOT / "data/processed/ml_research/exp-008-a"

SOURCE_MANIFEST_SHA256 = "d2fe121d592a5934753c555815a255620d0010838dc90957af5e3e73319a9cdb"

SOURCE_MODEL_SHA256 = "4f64df4485927c1fdc6eb4bd4a1d65f70a0d6dd9634e002c0f17a427a8d2a30c"

ARTIFACT_DIRECTORY = ROOT / "data/processed/experimental_ml/v2"

MAX_MODEL_BYTES = 64 * 1024 * 1024

PROMOTION_DECISION = "NO_ML_PROMOTION"
CAPACITY_APPLICATION_AUTHORIZED = False

# EXP-008's artifact fit and v1 support profile use the same original benchmark
# training partition. Pin both identities so v2 cannot silently borrow a profile
# from another fit. These are configuration receipts, never request parameters.
TRAINING_FINGERPRINT = "8ae08345a01c025b5e34a736b848100bc530c4987ac0d750543a7e07847171e8"
SUPPORT_PROFILE_SHA256 = "f2e50ecd9b0a589d88a3706f3a31a17f621a5de13b1bf3b9a33380dbaca1e4a3"

TRUSTED_MANIFEST_SHA256 = "55b09223c57e6c52261a71bc777edddc6116b88b8ffae3f7b0f9cc9075cc51f0"
