#!/usr/bin/env python3
"""按固定门槛定案高置信单字多音分配，并生成阶段性合并表。"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path


def split_map(value: str) -> Counter[str]:
    result: Counter[str] = Counter()
    for item in value.split(";"):
        if not item:
            continue
        key, count = item.rsplit(":", 1)
        result[key] += int(count)
    return result


def split_set(value: str) -> set[str]:
    return {item for item in value.split("/") if item}


def unique_dominant(counts: Counter[str]) -> str | None:
    positive = [(value, key) for key, value in counts.items() if value > 0]
    if not positive:
        return None
    maximum = max(value for value, _ in positive)
    winners = [key for value, key in positive if value == maximum]
    return winners[0] if len(winners) == 1 else None


def largest_remainder(total: int, weights: Counter[str]) -> dict[str, int]:
    weight_sum = sum(weights.values())
    if weight_sum <= 0:
        raise ValueError("分配权重总和必须大于0")
    exact = {key: Decimal(total) * Decimal(value) / Decimal(weight_sum) for key, value in weights.items()}
    allocated = {key: int(value) for key, value in exact.items()}
    remainder = total - sum(allocated.values())
    order = sorted(weights, key=lambda key: (-(exact[key] - allocated[key]), key))
    for key in order[:remainder]:
        allocated[key] += 1
    if sum(allocated.values()) != total:
        raise AssertionError("最大余数分配不守恒")
    return allocated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--priority-audit", type=Path, required=True)
    parser.add_argument("--stage2", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--minimum-unihan-samples", type=int, default=100)
    args = parser.parse_args()

    decisions: list[dict[str, object]] = []
    allocations: dict[tuple[str, str], int] = defaultdict(int)
    allocation_evidence: dict[tuple[str, str], str] = {}

    with args.priority_audit.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            char = row["汉字"]
            subtlex_set = split_set(row["SUBTLEX去调候选"])
            current_set = split_set(row["当前8454去调候选"])
            unihan = split_map(row["Unihan去调频率"])
            chai = split_map(row["Chai去调频率"])
            unihan_set = set(unihan)
            unihan_total = sum(unihan.values())
            unihan_dominant = unique_dominant(unihan)
            chai_dominant = unique_dominant(chai)
            reasons: list[str] = []
            if not unihan:
                reasons.append("Unihan未覆盖")
            if not (subtlex_set == current_set == unihan_set):
                reasons.append("三方去调读音集合不一致")
            if unihan_dominant is None:
                reasons.append("Unihan主读音不唯一")
            if chai_dominant is None:
                reasons.append("Chai主读音不唯一或无正频率")
            if unihan_dominant and chai_dominant and unihan_dominant != chai_dominant:
                reasons.append("Unihan与Chai主读音冲突")
            if unihan_total < args.minimum_unihan_samples:
                reasons.append(f"Unihan样本少于{args.minimum_unihan_samples}")

            status = "已定" if not reasons else "待复核"
            total_to_allocate = int(row["未分配频率"])
            if status == "已定":
                assigned = largest_remainder(total_to_allocate, unihan)
                for reading, frequency in assigned.items():
                    pair = (char, reading)
                    allocations[pair] += frequency
                    allocation_evidence[pair] = f"Unihan={unihan[reading]}/{unihan_total};SUBTLEX单字总频={total_to_allocate}"
            else:
                assigned = {}

            decisions.append({
                "影响排名": row["影响排名"],
                "汉字": char,
                "SUBTLEX单字总频": total_to_allocate,
                "SUBTLEX去调候选": "/".join(sorted(subtlex_set)),
                "当前8454候选": "/".join(sorted(current_set)),
                "Unihan频率": ";".join(f"{key}:{value}" for key, value in unihan.most_common()),
                "Unihan样本总数": unihan_total,
                "Unihan主读音": unihan_dominant or "",
                "Chai主读音": chai_dominant or "",
                "状态": status,
                "原因": "；".join(reasons),
                "分配结果": ";".join(f"{key}:{value}" for key, value in sorted(assigned.items())),
            })

    audit_path = args.output_dir / "SUBTLEX单字多音定案审计.tsv"
    with audit_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(decisions[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(decisions)

    allocation_path = args.output_dir / "SUBTLEX单字多音高置信分配.tsv"
    with allocation_path.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["汉字", "拼音", "已定分配频率", "证据", "状态"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for pair in sorted(allocations, key=lambda item: (-allocations[item], item[0], item[1])):
            writer.writerow({
                "汉字": pair[0],
                "拼音": pair[1],
                "已定分配频率": allocations[pair],
                "证据": allocation_evidence[pair],
                "状态": "已定：满足设计0026全部门槛",
            })

    stage_rows: list[dict[str, object]] = []
    with args.stage2.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            pair = (row["汉字"], row["拼音"])
            direct = int(row["直接唯一频率"])
            word_resolved = int(row["Chai整词消歧频率"])
            single_resolved = allocations[pair]
            stage_rows.append({
                "汉字": pair[0],
                "拼音": pair[1],
                "直接唯一频率": direct,
                "完整词条消歧频率": word_resolved,
                "高置信单字分配频率": single_resolved,
                "阶段性合计频率": direct + word_resolved + single_resolved,
                "状态": "阶段性候选；尚有待复核单字和未解决多字词",
            })
    stage_rows.sort(key=lambda row: (-int(row["阶段性合计频率"]), str(row["汉字"]), str(row["拼音"])))
    stage_path = args.output_dir / "SUBTLEX阶段性分读音频率表.tsv"
    with stage_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(stage_rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(stage_rows)

    settled = [row for row in decisions if row["状态"] == "已定"]
    pending = [row for row in decisions if row["状态"] != "已定"]
    settled_total = sum(int(row["SUBTLEX单字总频"]) for row in settled)
    pending_total = sum(int(row["SUBTLEX单字总频"]) for row in pending)
    report = {
        "minimum_unihan_samples": args.minimum_unihan_samples,
        "items_total": len(decisions),
        "items_settled": len(settled),
        "items_pending": len(pending),
        "single_word_frequency_settled": settled_total,
        "single_word_frequency_pending": pending_total,
        "settled_frequency_ratio": settled_total / (settled_total + pending_total),
        "allocation_conservation": sum(allocations.values()) == settled_total,
        "top30_settled": sum(row["状态"] == "已定" for row in decisions[:30]),
    }
    (args.output_dir / "SUBTLEX单字多音定案报告.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# SUBTLEX 单字多音高置信定案报告",
        "",
        f"- 门槛：Unihan 样本不少于 {args.minimum_unihan_samples}，三方读音集合一致，Unihan/Chai 主读音一致。",
        f"- 待分配项目：{len(decisions):,}",
        f"- 已定：{len(settled):,}",
        f"- 待复核：{len(pending):,}",
        f"- 已定单字词频：{settled_total:,}",
        f"- 剩余单字词频：{pending_total:,}",
        f"- 已定频率覆盖率：{report['settled_frequency_ratio']:.2%}",
        f"- 前 30 项已定：{report['top30_settled']}/30",
        f"- 分配守恒：{'是' if report['allocation_conservation'] else '否'}",
        "",
        "## 前 30 项状态",
        "",
        "| 排名 | 字 | 总频 | 状态 | 分配／原因 |",
        "|---:|:---:|---:|---|---|",
    ]
    for row in decisions[:30]:
        detail = row["分配结果"] if row["状态"] == "已定" else row["原因"]
        lines.append(f"| {row['影响排名']} | {row['汉字']} | {int(row['SUBTLEX单字总频']):,} | {row['状态']} | {detail} |")
    lines.extend(["", "本阶段未覆盖当前权威8454，也未重建退火元素。", ""])
    (args.output_dir / "SUBTLEX单字多音定案报告.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
