#!/usr/bin/env python3
"""Convert a two-column char/code table to code/char with round-trip checks."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse(path: Path, code_first: bool) -> list[tuple[str, str]]:
    rows = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        fields = raw.split("\t")
        if len(fields) != 2:
            raise SystemExit(f"invalid row {path}:{line_number}")
        code, char = fields if code_first else (fields[1], fields[0])
        if len(char) != 1 or not (1 <= len(code) <= 4 and code.isascii() and code.isalpha() and code.islower()):
            raise SystemExit(f"invalid char/code {path}:{line_number}: {raw!r}")
        rows.append((char, code))
    if not rows:
        raise SystemExit(f"empty table: {path}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.overwrite:
        raise SystemExit(f"output already exists: {args.output}")
    rows = parse(args.source, False)
    args.output.write_text("".join(f"{code}\t{char}\n" for char, code in rows), encoding="utf-8")
    if parse(args.output, True) != rows:
        raise SystemExit("round-trip mismatch")
    print(f"rows={len(rows)} status=pass")


if __name__ == "__main__":
    main()
