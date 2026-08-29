# -*- coding: utf-8 -*-
"""Rebuild the single authoritative common-character/common-word audit ledger."""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parents[1]
AUDIT = BASE / "work/v07_unlocked_audit"


def read_code(path: Path) -> list[list[str]]:
    return [
        line.split("\t")
        for line in path.read_text(encoding="utf-8").splitlines()
        if len(line.split("\t")) >= 4
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", type=Path, default=AUDIT / "简码冻结修复_最终校验.tsv")
    ap.add_argument(
        "--elements",
        type=Path,
        default=BASE / "work/v07_release_rebuild_20260826/elements_定稿排序_最新字形.yaml",
    )
    ap.add_argument(
        "--common",
        type=Path,
        default=AUDIT / "exact_common3527/内部前3300_并_外部前3000_3527字_原始资产_3527字.txt",
    )
    ap.add_argument("--word-top", type=int, default=20_000)
    ap.add_argument("--output", type=Path, default=AUDIT / "字词冲突主审计表.tsv")
    args = ap.parse_args()

    code_rows = read_code(args.code)
    elements = yaml.safe_load(args.elements.read_text(encoding="utf-8"))
    if len(code_rows) != len(elements):
        raise ValueError(f"code/elements 行数不一致：{len(code_rows)} != {len(elements)}")

    common = set(args.common.read_text(encoding="utf-8").splitlines())
    word_slots: dict[str, list[tuple[int, str]]] = defaultdict(list)
    lexicon = BASE / "work/lexicon/二字词_精选60000.tsv"
    with lexicon.open(encoding="utf-8-sig", newline="") as handle:
        for rank, row in enumerate(csv.DictReader(handle, delimiter="\t"), 1):
            if rank > args.word_top:
                break
            word_slots[row["code"]].append((rank, row["word"]))

    decision_data = yaml.safe_load((BASE / "work/字词冲突裁决.yaml").read_text(encoding="utf-8")) or {}
    decisions = decision_data.get("decisions") or {}
    policies = decision_data.get("policies") or {}

    output: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for row, element in zip(code_rows, elements):
        char, full, short = row[0], row[1], row[3]
        key = (char, full)
        if key in seen or char not in common or short != full or full not in word_slots:
            continue
        seen.add(key)
        hits = word_slots[full]
        decision = decisions.get(full)
        if decision and str(decision.get("char")) == char:
            status, source = "已处理", "统一裁决资产"
            note = str(decision.get("note") or "")
        elif (
            policies.get("same_initial_character") == "retain_single"
            and all(word.startswith(char) for _, word in hits)
        ):
            status, source = "已处理", "统一自动裁决规则"
            note = "同码词均以该字开头；保留单字首选，误出单字无需回删"
        else:
            status, source, note = "待审", "重新计算", ""
        rank = int(element.get("排序序号", 10**9)) + 1
        output.append({
            "字频序": rank,
            "单字": char,
            "全码": full,
            "当前简码": short,
            "二字词最高序": hits[0][0],
            "二字词": " ".join(word for _, word in hits),
            "状态": status,
            "结论／备注": note,
            "结论来源": source,
        })

    output.sort(key=lambda row: (int(row["字频序"]), str(row["全码"]), str(row["单字"])))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(output)

    handled = sum(row["状态"] == "已处理" for row in output)
    pending = len(output) - handled
    print(f"total={len(output)} handled={handled} pending={pending} output={args.output}")
    for row in output:
        if row["状态"] == "待审":
            print(f"待审\t{row['字频序']}\t{row['单字']}\t{row['全码']}\t{row['二字词']}")


if __name__ == "__main__":
    main()
