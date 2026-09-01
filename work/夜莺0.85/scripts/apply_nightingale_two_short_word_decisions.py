#!/usr/bin/env python3
"""把夜莺人工裁决应用到筛选后的简单鹤二简词表。"""

from __future__ import annotations

import argparse
from pathlib import Path


def read_tsv(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    headers = lines[0].split("\t")
    return [dict(zip(headers, line.split("\t"))) for line in lines[1:] if line]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--single", type=Path, required=True)
    parser.add_argument("--quick", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--move-audit", type=Path, required=True)
    args = parser.parse_args()

    source = read_tsv(args.source)
    decisions = read_tsv(args.decisions)
    buckets: dict[str, dict[int, str]] = {}
    for row in source:
        buckets.setdefault(row["简码"], {})[int(row["简单鹤候选位"])] = row["词"]

    for row in decisions:
        action = row["操作"]
        code = row["简码"]
        old_text = row["原词"]
        new_text = row["新词"]
        new_rank = int(row["新候选位"]) if row["新候选位"] else None
        bucket = buckets.setdefault(code, {})
        old_ranks = [rank for rank, text in bucket.items() if text == old_text] if old_text else []
        if action in {"替换", "移动", "删除"} and len(old_ranks) != 1:
            raise ValueError(f"{action}源条目应唯一命中：{code}={old_text}；实际{old_ranks}")
        if action in {"替换", "移动", "删除"}:
            del bucket[old_ranks[0]]
        if action in {"新增", "替换", "移动", "保留"}:
            if new_rank is None:
                raise ValueError(f"{action}缺少候选位：{code}={new_text}")
            occupied = bucket.get(new_rank)
            if occupied not in (None, new_text):
                raise ValueError(f"候选位冲突：{code},{new_rank}={new_text}；原值={occupied}")
            bucket[new_rank] = new_text

    single_counts: dict[str, int] = {}
    for raw in args.single.read_text(encoding="utf-8-sig").splitlines():
        text, code = raw.split("\t")
        if len(code) == 2 and len(text) == 1:
            single_counts[code] = single_counts.get(code, 0) + 1
    quick_slots: set[tuple[str, int]] = set()
    for raw in args.quick.read_text(encoding="utf-8-sig").splitlines():
        left, _text = raw.split("=", 1)
        code, rank_text = left.rsplit(",", 1)
        quick_slots.add((code, int(rank_text)))
    moves = ["简码\t词\t原候选位\t新候选位\t夜莺二码单字数\t原因"]
    for code, bucket in buckets.items():
        if (
            single_counts.get(code, 0) == 1
            and 3 in bucket
            and 2 not in bucket
            and (code, 2) not in quick_slots
        ):
            text = bucket.pop(3)
            bucket[2] = text
            moves.append(f"{code}\t{text}\t3\t2\t1\t夜莺仅一个二码单字且二候选为空")

    output = ["词\t简码\t候选位"]
    for code in sorted(buckets):
        for rank, text in sorted(buckets[code].items()):
            output.append(f"{text}\t{code}\t{rank}")
    args.output.write_text("\n".join(output) + "\n", encoding="utf-8")
    args.move_audit.write_text("\n".join(moves) + "\n", encoding="utf-8")
    print(f"rows={len(output) - 1} codes={len(buckets)} moved={len(moves) - 1}")


if __name__ == "__main__":
    main()
