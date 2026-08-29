#!/usr/bin/env python3
"""Append auditable F decisions for outside-head characters colliding with top words."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path


FIELDS = ["裁决编号", "码", "调整前关键候选", "调整后关键候选", "理由", "状态"]


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def stable_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def read_combined_slots(path: Path) -> dict[str, list[str]]:
    slots: dict[str, list[str]] = defaultdict(list)
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw in enumerate(handle, 1):
            line = raw.rstrip("\r\n")
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) != 2:
                raise SystemExit(f"invalid combined row {line_number}: {line!r}")
            content, code = parts
            slots[code].append(content)
    return slots


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--collisions", type=Path, required=True)
    parser.add_argument("--combined", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--head", type=int, default=3527)
    parser.add_argument("--word-top", type=int, default=20000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    audit = read_tsv(args.audit)
    collisions = read_tsv(args.collisions)
    combined_slots = read_combined_slots(args.combined)
    decisions = read_tsv(args.decisions)

    head_chars = {
        row["字"] for row in audit if row.get("原始行号", "").isdigit() and int(row["原始行号"]) <= args.head
    }
    known_actual_pairs = {(row["字"], row["实际码"]) for row in audit}
    head_actual_pairs = {
        (row["字"], row["实际码"])
        for row in audit
        if row.get("原始行号", "").isdigit() and int(row["原始行号"]) <= args.head
    }
    existing_codes = {row["码"] for row in decisions}

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in collisions:
        if row.get("status") != "直接撞车待审":
            continue
        rank = row.get("two_top_rank", "")
        if not rank.isdigit() or int(rank) > args.word_top:
            continue
        grouped[row["code"]].append(row)

    eligible: list[tuple[int, str, list[str], list[str]]] = []
    for code, rows in grouped.items():
        chars = stable_unique([row["char"] for row in rows])
        identity_is_head = []
        for char in chars:
            pair = (char, code)
            if pair in known_actual_pairs:
                identity_is_head.append(pair in head_actual_pairs)
            else:
                # Conservative fallback for manually moved codes that cannot be
                # joined exactly to the original identity audit.
                identity_is_head.append(char in head_chars)
        if any(identity_is_head):
            continue
        if code in existing_codes:
            continue
        rank = min(int(row["two_top_rank"]) for row in rows)
        words = stable_unique(rows[0].get("two_words", "").split())
        if not words:
            continue
        eligible.append((rank, code, chars, words))

    eligible.sort(key=lambda item: (item[0], item[1]))
    existing_ids = []
    for row in decisions:
        raw = row.get("裁决编号", "")
        if raw.startswith("G8C12-W") and raw[7:].isdigit():
            existing_ids.append(int(raw[7:]))
    next_id = max(existing_ids, default=0) + 1

    additions: list[dict[str, str]] = []
    for rank, code, chars, words in eligible:
        before = stable_unique(combined_slots.get(code, []))
        if words[0] not in before:
            raise SystemExit(f"top word {words[0]!r} missing from combined slot {code}")
        after = [words[0]] + [item for item in before if item != words[0]]
        additions.append(
            {
                "裁决编号": f"G8C12-W{next_id:03d}",
                "码": code,
                "调整前关键候选": "、".join(before),
                "调整后关键候选": "、".join(after),
                "理由": (
                    f"自动规则：同码全部单字均在前{args.head}之外，且最高二字词排名"
                    f"{rank}≤{args.word_top}；单字整体只让一个首选位置。"
                ),
                "状态": f"规则自动让位：前{args.head}外撞前{args.word_top}词",
            }
        )
        next_id += 1

    print(f"eligible={len(additions)} existing={len(decisions)} dry_run={args.dry_run}")
    for row in additions:
        print(f"{row['裁决编号']}\t{row['码']}\t{row['调整后关键候选']}")

    if args.dry_run or not additions:
        return

    output_rows = decisions + additions
    ids = [row["裁决编号"] for row in output_rows]
    codes = [row["码"] for row in output_rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate decision id")
    if len(codes) != len(set(codes)):
        raise SystemExit("duplicate decision code")

    temporary = args.decisions.with_suffix(args.decisions.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(output_rows)
    temporary.replace(args.decisions)


if __name__ == "__main__":
    main()
