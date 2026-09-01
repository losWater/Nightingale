#!/usr/bin/env python3
"""生成低于20万条上限的搜狗五笔原生码表（排除扩展字）。"""

from __future__ import annotations

import argparse
from collections import OrderedDict
from pathlib import Path


LIMIT = 200_000


def read_pairs(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw:
            continue
        parts = raw.split("\t")
        if len(parts) != 2:
            raise ValueError(f"{path}:{number}: 应为‘字词<Tab>编码’")
        rows.append((parts[0], parts[1]))
    return rows


def read_extension_characters(path: Path) -> set[str]:
    rows = path.read_text(encoding="utf-8-sig").splitlines()
    return {raw.split("\t", 1)[0] for raw in rows[1:] if raw}


def read_quick(path: Path) -> list[tuple[str, int, str]]:
    rows: list[tuple[str, int, str]] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if not raw:
            continue
        left, text = raw.split("=", 1)
        code, rank = left.rsplit(",", 1)
        rows.append((code, int(rank), text))
    return rows


def build(combined: list[tuple[str, str]], extension: set[str], quick: list[tuple[str, int, str]]) -> list[tuple[str, str]]:
    buckets: OrderedDict[str, list[str]] = OrderedDict()
    for text, code in combined:
        if len(text) == 1 and text in extension:
            continue
        buckets.setdefault(code, []).append(text)
    for code, rank, text in quick:
        bucket = buckets.setdefault(code, [])
        if text in bucket:
            bucket.remove(text)
        bucket.insert(min(max(rank - 1, 0), len(bucket)), text)
    return [(code, text) for code, texts in buckets.items() for text in texts]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--combined", type=Path, required=True)
    parser.add_argument("--extension-characters", type=Path, required=True)
    parser.add_argument("--quick", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    combined = read_pairs(args.combined)
    extension = read_extension_characters(args.extension_characters)
    quick = read_quick(args.quick)
    rows = build(combined, extension, quick)
    if len(rows) > LIMIT:
        raise ValueError(f"搜狗五笔码表超过 {LIMIT} 条：{len(rows)}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(("\n".join(f"{code}\t{text}" for code, text in rows) + "\n").encode("utf-8"))
    print(f"搜狗五笔原生码表：{len(rows)} 条；排除扩展字 {len(extension)} 个；余量 {LIMIT - len(rows)} 条")


if __name__ == "__main__":
    main()
