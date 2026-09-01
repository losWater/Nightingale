#!/usr/bin/env python3
"""将已验收的尾部分配预览接入阶段表，并显式保留残余未分配频率。"""

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
            raise ValueError(f"重复读音：{reading}")
        result[reading] = int(frequency)
    return result


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--preview", type=Path, required=True)
    parser.add_argument("--anomalies", type=Path, required=True)
    parser.add_argument("--source-audit", type=Path, required=True)
    parser.add_argument("--special-weights", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    stage_rows = read_tsv(args.stage)
    preview_rows = read_tsv(args.preview)
    anomaly_rows = read_tsv(args.anomalies)
    source_by_char = {row["汉字"]: row for row in read_tsv(args.source_audit)}
    special = json.loads(args.special_weights.read_text(encoding="utf-8"))
    special_chars = {rule["character"] for rule in special["rules"]}

    base: dict[tuple[str, str], int] = {}
    for row in stage_rows:
        base[(row["汉字"], row["拼音"])] = int(row["人工定案后阶段频率"])

    additions: dict[tuple[str, str], int] = defaultdict(int)
    allocated_chars: set[str] = set()
    for row in preview_rows:
        char = row["汉字"]
        expected = int(row["待分配频率"])
        allocation = parse_allocation(row["分配结果"])
        if sum(allocation.values()) != expected:
            raise ValueError(f"{char} 预览分配不守恒")
        for reading, frequency in allocation.items():
            pair = (char, reading)
            if pair not in base:
                raise ValueError(f"预览分配到阶段表不存在的身份：{pair}")
            additions[pair] += frequency
        allocated_chars.add(char)

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
            "尾部分配前频率": base[pair],
            "尾部分配新增频率": addition,
            "退火候选自然频率": base[pair] + addition,
            "状态": "退火自然频率候选；特殊优化权重另层应用",
        })
    output_rows.sort(key=lambda row: (-int(row["退火候选自然频率"]), str(row["汉字"]), str(row["拼音"])))

    residual: list[dict[str, str | int]] = []
    for row in anomaly_rows:
        residual.append({
            "汉字": row["汉字"],
            "未分配频率": int(row["待分配频率"]),
            "处理状态": "保持未分配",
            "原因": row["异常原因"],
        })
    for char in sorted(special_chars):
        if char not in source_by_char:
            raise ValueError(f"特殊权重字不在单字审计：{char}")
        residual.append({
            "汉字": char,
            "未分配频率": int(source_by_char[char]["SUBTLEX单字总频"]),
            "处理状态": "自然频率保持未分配；退火使用特殊优化权重",
            "原因": "见特殊优化权重裁决.json",
        })
    residual.sort(key=lambda row: (-int(row["未分配频率"]), str(row["汉字"])))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "SUBTLEX分读音频率表_退火候选版.tsv"
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(output_rows)
    residual_path = args.output_dir / "退火候选仍未分配频率.tsv"
    with residual_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(residual[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(residual)

    unchanged_ok = all(
        int(row["退火候选自然频率"]) == base[(str(row["汉字"]), str(row["拼音"]))]
        for row in output_rows
        if (str(row["汉字"]), str(row["拼音"])) not in changed_pairs
    )
    report = {
        "allocated_characters": len(allocated_chars),
        "allocated_frequency": sum(additions.values()),
        "changed_pairs": len(changed_pairs),
        "all_other_pairs_unchanged": unchanged_ok,
        "residual_items": len(residual),
        "residual_frequency": sum(int(row["未分配频率"]) for row in residual),
        "output_sha256": sha256(output_path),
        "residual_sha256": sha256(residual_path),
    }
    (args.output_dir / "尾部分配正式接线报告.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# 尾部分配正式接线报告", "",
        f"- 接入：{report['allocated_characters']} 字，频率 {report['allocated_frequency']:,}",
        f"- 变化字音对：{report['changed_pairs']}",
        f"- 其他字音对不变：{'是' if report['all_other_pairs_unchanged'] else '否'}",
        f"- 仍未分配：{report['residual_items']} 项，频率 {report['residual_frequency']:,}", "",
        "特殊优化权重仍须在退火输入生成阶段独立应用，本表不以优化权重改写自然频率。", ""
    ]
    (args.output_dir / "尾部分配正式接线报告.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
