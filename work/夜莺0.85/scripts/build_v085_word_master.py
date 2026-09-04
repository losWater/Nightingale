#!/usr/bin/env python3
"""把普通字词底表与简词裁决表合并为完整的夜莺 0.9 字词主表。"""

from __future__ import annotations

import argparse
from collections import OrderedDict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ordinary", type=Path, required=True)
    parser.add_argument("--short-words", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    buckets: OrderedDict[str, list[str]] = OrderedDict()
    for line_number, raw in enumerate(args.ordinary.read_text(encoding="utf-8-sig").splitlines(), 1):
        parts = raw.split("\t")
        if len(parts) != 2:
            raise ValueError(f"{args.ordinary}:{line_number}: 应为‘字词<Tab>编码’")
        text, code = parts
        buckets.setdefault(code, []).append(text)

    reserved: OrderedDict[str, dict[int, str]] = OrderedDict()
    for line_number, raw in enumerate(args.short_words.read_text(encoding="utf-8-sig").splitlines()[1:], 2):
        if not raw:
            continue
        text, code, rank_text, _level = raw.split("\t")
        rank = int(rank_text)
        previous = reserved.setdefault(code, {}).get(rank)
        if previous is not None and previous != text:
            raise ValueError(f"{args.short_words}:{line_number}: 简词位置冲突 {code},{rank}")
        reserved[code][rank] = text

    code_order = list(buckets) + [code for code in reserved if code not in buckets]
    output: list[str] = []
    for code in code_order:
        merged = dict(reserved.get(code, {}))
        for text in buckets.get(code, []):
            if text in merged.values():
                continue
            rank = 1
            while rank in merged:
                rank += 1
            merged[rank] = text
        output.extend(f"{text}\t{code}" for _rank, text in sorted(merged.items()))

    args.output.write_bytes(("\n".join(output) + "\n").encode("utf-8"))
    print(f"普通底表={sum(map(len, buckets.values()))} 简词={sum(map(len, reserved.values()))} 综合主表={len(output)}")


if __name__ == "__main__":
    main()
