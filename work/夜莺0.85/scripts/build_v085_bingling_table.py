#!/usr/bin/env python3
"""生成冰凌输入法词库（UTF-16 LE + CRLF；含扩展字低频、快符与夜莺构词规则）。"""

from __future__ import annotations

import argparse
from collections import OrderedDict
from datetime import date
from pathlib import Path


REGULAR_TOP = 9999
REGULAR_FLOOR = 256
RARE_FREQUENCY = 11

HEADER_LINES = (
    "[CODETABLEHEADER]",
    "Name=夜莺码词库",
    "Version=0.8.5|{stamp}",
    "Author=nightingale",
    "CodeScheme=夜莺码0.8.5[夜莺]",
    "CodeLength=4",
    "BWCodeLength=0",
    "SpecialPrefix=0",
    "PhraseRule=3",
    "pa2=w11w12w21w22",
    "pa3=w11w21w31",
    "pe4=w11w21w31r11",
    "[CODETABLE]",
)


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


def is_host_macro(text: str) -> bool:
    return "$ddcmd(" in text or text.startswith("#$(")


def build(combined: list[tuple[str, str]], extension: set[str],
          quick: list[tuple[str, int, str]]) -> tuple[list[tuple[str, str, int]], int]:
    buckets: OrderedDict[str, list[str]] = OrderedDict()
    skipped_macros = 0
    for text, code in combined:
        if is_host_macro(text):
            skipped_macros += 1
            continue
        buckets.setdefault(code, []).append(text)
    for code, rank, text in quick:
        bucket = buckets.setdefault(code, [])
        if text in bucket:
            bucket.remove(text)
        bucket.insert(min(max(rank - 1, 0), len(bucket)), text)
    rows: list[tuple[str, str, int]] = []
    for code in sorted(buckets):
        for position, text in enumerate(buckets[code]):
            if len(text) == 1 and text in extension:
                frequency = RARE_FREQUENCY
            else:
                frequency = max(REGULAR_TOP - position, REGULAR_FLOOR)
            rows.append((code, text, frequency))
    return rows, skipped_macros


def render(rows: list[tuple[str, str, int]], stamp: str) -> str:
    lines = [line.format(stamp=stamp) for line in HEADER_LINES]
    lines.extend(f"{code}\t{text}\t{frequency}" for code, text, frequency in rows)
    return "\r\n".join(lines) + "\r\n"


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
    rows, skipped_macros = build(combined, extension, quick)
    stamp = date.today().strftime("%y%m%d")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(b"\xff\xfe" + render(rows, stamp).encode("utf-16-le"))
    rare = sum(1 for _code, _text, frequency in rows if frequency == RARE_FREQUENCY)
    print(f"冰凌词库：{len(rows)} 条；扩展字低频 {rare} 条；排除宿主命令词 {skipped_macros} 条")


if __name__ == "__main__":
    main()
