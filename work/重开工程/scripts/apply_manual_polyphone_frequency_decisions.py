#!/usr/bin/env python3
"""把正式人工裁决应用到阶段性分读音频率表，保持总频守恒。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def parse_allocation(value: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in value.split(";"):
        reading, frequency = item.rsplit(":", 1)
        if reading in result:
            raise ValueError(f"分配结果重复读音：{reading}")
        result[reading] = int(frequency)
    return result


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--source-audit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    decisions = read_tsv(args.decisions)
    stage_rows = read_tsv(args.stage)
    source_rows = read_tsv(args.source_audit)
    source_by_char = {row["汉字"]: row for row in source_rows}
    stage_readings: dict[str, set[str]] = defaultdict(set)
    before_by_pair: dict[tuple[str, str], int] = {}
    for row in stage_rows:
        pair = (row["汉字"], row["拼音"])
        stage_readings[pair[0]].add(pair[1])
        before_by_pair[pair] = int(row["封闭集合阶段合计频率"])

    additions: dict[tuple[str, str], int] = defaultdict(int)
    audit_rows: list[dict[str, str | int]] = []
    for decision in decisions:
        char = decision["汉字"]
        expected_pending = int(decision["待分配频率"])
        if char not in source_by_char:
            raise ValueError(f"原审计中没有 {char}")
        source_pending = int(source_by_char[char]["SUBTLEX单字总频"])
        if source_pending != expected_pending:
            raise ValueError(f"{char} 待分配频率变化：期望 {expected_pending}，实际 {source_pending}")
        allocation = parse_allocation(decision["分配结果"])
        if set(allocation) - stage_readings[char]:
            raise ValueError(f"{char} 分配到封闭集合外读音：{set(allocation) - stage_readings[char]}")
        if sum(allocation.values()) != expected_pending:
            raise ValueError(f"{char} 分配不守恒：{sum(allocation.values())} != {expected_pending}")
        before_total = sum(before_by_pair[(char, reading)] for reading in stage_readings[char])
        for reading, frequency in allocation.items():
            additions[(char, reading)] += frequency
        audit_rows.append({
            "汉字": char,
            "原阶段总频": before_total,
            "待分配频率": expected_pending,
            "分配结果": decision["分配结果"],
            "定案后整字总频": before_total + expected_pending,
            "守恒": "是",
            "裁决依据": decision["裁决依据"],
        })

    output_rows: list[dict[str, str | int]] = []
    changed_pairs: set[tuple[str, str]] = set()
    for row in stage_rows:
        pair = (row["汉字"], row["拼音"])
        addition = additions[pair]
        if addition:
            changed_pairs.add(pair)
        output_rows.append({
            "汉字": pair[0],
            "拼音": pair[1],
            "人工定案前阶段频率": before_by_pair[pair],
            "人工定案新增频率": addition,
            "人工定案后阶段频率": before_by_pair[pair] + addition,
            "状态": "阶段性候选；当前8454封闭；人工定案已应用",
        })
    output_rows.sort(key=lambda row: (-int(row["人工定案后阶段频率"]), str(row["汉字"]), str(row["拼音"])))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "SUBTLEX阶段性分读音频率表_人工定案版.tsv"
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(output_rows)
    audit_path = args.output_dir / "多音字人工频率定案审计.tsv"
    with audit_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit_rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(audit_rows)

    unchanged_ok = all(
        int(row["人工定案后阶段频率"]) == before_by_pair[(str(row["汉字"]), str(row["拼音"]))]
        for row in output_rows
        if (str(row["汉字"]), str(row["拼音"])) not in changed_pairs
    )
    report = {
        "decision_count": len(decisions),
        "allocated_frequency": sum(additions.values()),
        "changed_pairs": sorted([list(pair) for pair in changed_pairs]),
        "all_other_pairs_unchanged": unchanged_ok,
        "output_sha256": sha256(output_path),
        "audit_sha256": sha256(audit_path),
    }
    (args.output_dir / "多音字人工频率定案报告.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
