#!/usr/bin/env python3
"""按夜莺三码单字位重排三简词，压缩空位并顺延撞位。"""

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
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--single", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--move-audit", type=Path, required=True)
    parser.add_argument("--backward-audit", type=Path, required=True)
    args = parser.parse_args()

    rows = read_tsv(args.source)
    buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        buckets[row["简码"]].append(row)
    singles: dict[str, str] = {}
    for raw in args.single.read_text(encoding="utf-8-sig").splitlines():
        text, code = raw.split("\t")
        if len(code) == 3:
            singles[code] = text

    moves = ["简码\t词\t原候选位\t新候选位\t前移距离\t夜莺三码单字"]
    backward = ["简码\t词\t原候选位\t新候选位\t后移距离\t夜莺三码单字"]
    output_rows: list[tuple[str, int, str]] = []
    for code in sorted(buckets):
        ordered = sorted(buckets[code], key=lambda row: (int(row["简单鹤候选位"]), row["词"]))
        base = 2 if code in singles else 1
        targets = [base + index for index in range(len(ordered))]
        old_ranks = [int(row["简单鹤候选位"]) for row in ordered]
        for row, old_rank, new_rank in zip(ordered, old_ranks, targets):
            output_rows.append((code, new_rank, row["词"]))
            if new_rank < old_rank:
                moves.append(
                    f"{code}\t{row['词']}\t{old_rank}\t{new_rank}\t{old_rank - new_rank}\t{singles.get(code, '')}"
                )
            elif new_rank > old_rank:
                backward.append(
                    f"{code}\t{row['词']}\t{old_rank}\t{new_rank}\t{new_rank - old_rank}\t{singles.get(code, '')}"
                )

    output = ["词\t简码\t候选位"] + [
        f"{text}\t{code}\t{rank}" for code, rank, text in sorted(output_rows)
    ]
    args.output.write_text("\n".join(output) + "\n", encoding="utf-8")
    args.move_audit.write_text("\n".join(moves) + "\n", encoding="utf-8")
    args.backward_audit.write_text("\n".join(backward) + "\n", encoding="utf-8")
    print(
        f"rows={len(output_rows)} moved={len(moves) - 1} "
        f"moved_backward={len(backward) - 1}"
    )


if __name__ == "__main__":
    main()
