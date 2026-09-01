#!/usr/bin/env python3
"""将四简词追加到夜莺综合字词与快符候选桶末尾。"""

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
    parser.add_argument("--combined", type=Path, required=True)
    parser.add_argument("--quick", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()

    existing: dict[str, list[str]] = defaultdict(list)
    for raw in args.combined.read_text(encoding="utf-8-sig").splitlines():
        text, code = raw.split("\t")
        existing[code].append(text)
    occupied_ranks: dict[str, set[int]] = {
        code: set(range(1, len(items) + 1)) for code, items in existing.items()
    }
    for raw in args.quick.read_text(encoding="utf-8-sig").splitlines():
        left, _text = raw.split("=", 1)
        code, rank_text = left.rsplit(",", 1)
        occupied_ranks.setdefault(code, set()).add(int(rank_text))

    source = read_tsv(args.source)
    buckets: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in source:
        buckets[row["简码"]].append(row)
    output = ["词\t简码\t候选位"]
    audit = ["词\t简码\t简单鹤候选位\t处理\t夜莺候选位\t原因"]
    already_existing = 0
    appended = 0
    for code in sorted(buckets):
        seen_texts = set(existing.get(code, []))
        next_rank = max(occupied_ranks.get(code, set()), default=0) + 1
        for row in sorted(buckets[code], key=lambda item: (int(item["简单鹤候选位"]), item["词"])):
            text = row["词"]
            if text in seen_texts:
                already_existing += 1
                audit.append(
                    f"{text}\t{code}\t{row['简单鹤候选位']}\t去重\t\t综合字词主表已有相同词码"
                )
                continue
            while next_rank in occupied_ranks.setdefault(code, set()):
                next_rank += 1
            output.append(f"{text}\t{code}\t{next_rank}")
            audit.append(
                f"{text}\t{code}\t{row['简单鹤候选位']}\t追加\t{next_rank}\t排在综合字词与快符候选之后"
            )
            seen_texts.add(text)
            occupied_ranks[code].add(next_rank)
            next_rank += 1
            appended += 1

    args.output.write_text("\n".join(output) + "\n", encoding="utf-8")
    args.audit.write_text("\n".join(audit) + "\n", encoding="utf-8")
    print(
        f"source={len(source)} appended={appended} already_existing={already_existing} "
        f"codes={len({row['简码'] for row in source})}"
    )


if __name__ == "__main__":
    main()
