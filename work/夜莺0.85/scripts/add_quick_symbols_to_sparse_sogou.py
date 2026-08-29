#!/usr/bin/env python3
"""Merge quick symbols into a sparse-position Sogou char table."""

from __future__ import annotations

import argparse
from collections import OrderedDict
from pathlib import Path


def parse(path: Path) -> tuple[list[str], OrderedDict[str, dict[int, str]]]:
    headers = []
    slots: OrderedDict[str, dict[int, str]] = OrderedDict()
    for line_number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw:
            continue
        if raw.startswith(";"):
            headers.append(raw)
            continue
        left, separator, value = raw.partition("=")
        code, comma, position = left.rpartition(",")
        if not separator or not comma or not position.isdigit():
            raise SystemExit(f"invalid row {path}:{line_number}: {raw!r}")
        index = int(position)
        bucket = slots.setdefault(code, {})
        if index in bucket:
            raise SystemExit(f"duplicate slot {code},{index} in {path}")
        bucket[index] = value
    return headers, slots


def triples(slots: OrderedDict[str, dict[int, str]]) -> set[tuple[str, int, str]]:
    return {(code, index, value) for code, bucket in slots.items() for index, value in bucket.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--quick", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"output already exists: {args.output}")

    headers, slots = parse(args.source)
    _, quick_slots = parse(args.quick)
    before = triples(slots)
    quick_count = 0
    for code, bucket in quick_slots.items():
        target = slots.setdefault(code, {})
        for index, value in bucket.items():
            if index in target:
                raise SystemExit(f"quick symbol collision: {code},{index}={value}; source={target[index]}")
            target[index] = value
            quick_count += 1
    if not before.issubset(triples(slots)):
        raise SystemExit("source entry changed during merge")

    lines = list(headers)
    if lines:
        lines.append("; 加入既有快符；保留因词位让位产生的稀疏候选序号")
    for code, bucket in slots.items():
        for index in sorted(bucket):
            lines.append(f"{code},{index}={bucket[index]}")
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    _, verify = parse(args.output)
    if triples(verify) != triples(slots):
        raise SystemExit("output round-trip mismatch")
    print(f"source_entries={len(before)} quick_entries={quick_count} result_entries={len(triples(slots))}")


if __name__ == "__main__":
    main()
