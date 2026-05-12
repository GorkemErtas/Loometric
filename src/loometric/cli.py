"""Local command-line orchestration. All computation stays on this machine."""

import argparse
import sys
from pathlib import Path

from loometric.data.loading import DatasetReadError, clean_data, read_csv
from loometric.data.profiling import build_profile, fingerprint
from loometric.data.validation import validate_data

DEFAULT_DATASET = Path("data/raw/garments_worker_productivity.csv")
DEFAULT_OUTPUT = Path("docs/data_profile.md")


def main(argv: list[str] | None = None) -> int:
    """Write a profile; return 0 for valid data, 1 for validation errors, 2 for I/O errors."""
    parser = argparse.ArgumentParser(description="Local Loometric data validation and profiling.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET, help="Source CSV path.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Markdown report path.")
    args = parser.parse_args(argv)
    if args.dataset.resolve() == args.output.resolve():
        print("error: report path must differ from source dataset path.", file=sys.stderr)
        return 2
    try:
        raw = read_csv(args.dataset)
    except FileNotFoundError:
        print(
            f"error: dataset not found: {args.dataset}. Place the CSV there and rerun.",
            file=sys.stderr,
        )
        return 2
    except (OSError, DatasetReadError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    clean = clean_data(raw)
    validation = validate_data(raw, clean)
    # Only the filename is recorded for inputs outside the working tree.
    source_label = (
        args.dataset.resolve().relative_to(Path.cwd().resolve())
        if args.dataset.resolve().is_relative_to(Path.cwd().resolve())
        else Path(args.dataset.name)
    )
    try:
        report = build_profile(
            raw, clean, validation, source=source_label, source_sha256=fingerprint(args.dataset)
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8", newline="\n")
    except OSError as exc:
        print(f"error: cannot write profile: {exc}", file=sys.stderr)
        return 2
    errors = sum(issue.severity == "error" for issue in validation.issues)
    warnings = sum(issue.severity == "warning" for issue in validation.issues)
    print(
        f"{'PASS' if validation.passed else 'FAIL'}: {len(raw)} rows; "
        f"{errors} error checks; {warnings} warning checks. Report: {args.output}"
    )
    return 0 if validation.passed else 1
