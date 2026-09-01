#!/usr/bin/env python3
"""将二简中含“一”的词成组放到第二候选起，顺延其余候选。"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path


def read_tsv(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    headers = lines[0].split("\t")
    return [dict(zip(headers, line.split("\t"))) for line in lines[1:] if line]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adaptation-audit", type=Path, required=True)
    parser.add_argument("--single", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()

    buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_tsv(args.adaptation_audit):
        buckets[row["夜莺简码"]].append(row)
    single_codes: set[str] = set()
    for raw in args.single.read_text(encoding="utf-8-sig").splitlines():
        text, code = raw.split("\t")
        if len(text) == 1 and len(code) == 2:
            single_codes.add(code)
    output = ["词\t简码\t简单鹤候选位\t来源"]
    audit = ["简码\t词\t原简码\t原候选位\t新候选位\t处理"]
    yi_count = 0
    shifted_count = 0
    for code in sorted(buckets):
        rows = buckets[code]
        order_key = lambda row: (
            int(row["候选位"]),
            row["原简码"] != row["夜莺简码"],
            row["词"],
        )
        first_non_yi = sorted(
            (row for row in rows if "一" not in row["词"] and int(row["候选位"]) == 1),
            key=order_key,
        )
        yi_rows = sorted((row for row in rows if "一" in row["词"]), key=order_key)
        other_rows = sorted(
            (row for row in rows if "一" not in row["词"] and int(row["候选位"]) != 1),
            key=order_key,
        )
        arranged: list[tuple[dict[str, str], int]] = []
        if code not in single_codes and first_non_yi:
            arranged.append((first_non_yi[0], 1))
            other_rows = first_non_yi[1:] + other_rows
        else:
            other_rows = first_non_yi + other_rows
        next_rank = 2 if arranged or code in single_codes or yi_rows else 1
        for row in yi_rows:
            arranged.append((row, next_rank))
            next_rank += 1
            yi_count += 1
        for row in other_rows:
            arranged.append((row, next_rank))
            next_rank += 1
        for row, new_rank in arranged:
            old_rank = int(row["候选位"])
            if new_rank != old_rank:
                shifted_count += 1
            output.append(f"{row['词']}\t{code}\t{new_rank}\t简单鹤二简（一词二选规则）")
            audit.append(
                f"{code}\t{row['词']}\t{row['原简码']}\t{old_rank}\t{new_rank}\t"
                + ("含一：从二候选起排列" if "一" in row["词"] else "为含一词顺延")
            )
    args.output.write_text("\n".join(output) + "\n", encoding="utf-8")
    args.audit.write_text("\n".join(audit) + "\n", encoding="utf-8")
    print(f"rows={len(output) - 1} yi_words={yi_count} changed_positions={shifted_count}")


if __name__ == "__main__":
    main()
