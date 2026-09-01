#!/usr/bin/env python3
"""合并夜莺二简、三简、四简为唯一简词主表。"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read(path: Path, level: int) -> list[tuple[str, str, int, int]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    return [(row["词"], row["简码"], int(row["候选位"]), level) for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--two", type=Path, required=True)
    parser.add_argument("--three", type=Path, required=True)
    parser.add_argument("--four", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = read(args.two, 2) + read(args.three, 3) + read(args.four, 4)
    slots: dict[tuple[str, int], str] = {}
    word_codes: set[tuple[str, str]] = set()
    for text, code, rank, level in rows:
        if len(code) != level:
            raise ValueError(f"简词级别不符：{text} {code} level={level}")
        if (code, rank) in slots:
            raise ValueError(f"候选位重复：{code},{rank}={text}；原值={slots[(code, rank)]}")
        if (text, code) in word_codes:
            raise ValueError(f"词码重复：{text} {code}")
        slots[(code, rank)] = text
        word_codes.add((text, code))
    output = ["词\t简码\t候选位\t级别"] + [
        f"{text}\t{code}\t{rank}\t{level}"
        for text, code, rank, level in sorted(rows, key=lambda row: (row[1], row[2], row[0]))
    ]
    args.output.write_text("\n".join(output) + "\n", encoding="utf-8")
    print(f"rows={len(rows)} codes={len({code for _, code, _, _ in rows})}")


if __name__ == "__main__":
    main()
