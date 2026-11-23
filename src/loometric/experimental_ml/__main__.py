"""Explicit offline publication. Inference never invokes this command."""

import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish fixed M08B experimental models locally.")
    parser.add_argument("command", choices=["publish"])
    parser.add_argument("--version", choices=["v1", "v1-reproduction"], required=True)
    args = parser.parse_args()
    from loometric.experimental_ml.publish import publish_version

    try:
        print(json.dumps(publish_version(args.version), sort_keys=True))
        return 0
    except (OSError, ValueError):
        parser.exit(1, "Experimental publication failed; inspect the trusted offline inputs.\n")


if __name__ == "__main__":
    raise SystemExit(main())
