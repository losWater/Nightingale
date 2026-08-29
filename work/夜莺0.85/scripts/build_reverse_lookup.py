#!/usr/bin/env python3
"""Build the formal offline code-to-character/word lookup page."""

from __future__ import annotations

import argparse
from pathlib import Path

from build_v085_release import build_reverse_lookup


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--combined", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.overwrite:
        raise SystemExit(f"output already exists: {args.output}")
    codes, entries = build_reverse_lookup(args.combined, args.output)
    print(f"codes={codes} entries={entries} status=pass")


if __name__ == "__main__":
    main()
