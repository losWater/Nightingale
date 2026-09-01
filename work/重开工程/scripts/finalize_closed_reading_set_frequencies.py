#!/usr/bin/env python3
"""在当前8454封闭读音集合内，继续定案此前待复核的单字词频。"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path


def split_set(value: str) -> set[str]:
    return {item for item in value.split("/") if item}


def split_counts(value: str) -> Counter[str]:
    result: Counter[str] = Counter()
    for item in value.split(";"):
        if item:
            key, count = item.rsplit(":", 1)
            result[key] += int(count)
    return result


def dominant(counts: Counter[str]) -> str | None:
    positive = [(count, key) for key, count in counts.items() if count > 0]
    if not positive:
        return None
    maximum = max(count for count, _ in positive)
    winners = [key for count, key in positive if count == maximum]
    return winners[0] if len(winners) == 1 else None


def largest_remainder(total: int, weights: Counter[str], universe: set[str]) -> dict[str, int]:
    weight_sum = sum(weights.values())
    if weight_sum <= 0:
        raise ValueError("权重总和必须大于0")
    exact = {key: Decimal(total) * Decimal(weights.get(key, 0)) / Decimal(weight_sum) for key in universe}
    allocated = {key: int(value) for key, value in exact.items()}
    remainder = total - sum(allocated.values())
    order = sorted(universe, key=lambda key: (-(exact[key] - allocated[key]), key))
    for key in order[:remainder]:
        allocated[key] += 1
    if sum(allocated.values()) != total:
        raise AssertionError("分配不守恒")
    return allocated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--source-audit", type=Path, required=True)
    parser.add_argument("--stage-table", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--minimum-unihan-samples", type=int, default=100)
    args = parser.parse_args()

    source_by_char: dict[str, dict[str, str]] = {}
    with args.source_audit.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            source_by_char[row["汉字"]] = row

    audit_rows: list[dict[str, object]] = []
    new_allocations: dict[tuple[str, str], int] = defaultdict(int)
    with args.decisions.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["状态"] == "已定":
                continue
            char = row["汉字"]
            source = source_by_char[char]
            current = split_set(row["当前8454候选"])
            unihan_all = split_counts(source["Unihan去调频率"])
            chai_all = split_counts(source["Chai去调频率"])
            unihan_current = Counter({key: unihan_all[key] for key in current if unihan_all[key] > 0})
            missing_in_unihan = current - set(unihan_current)
            reasons: list[str] = []
            basis = ""
            total = int(row["SUBTLEX单字总频"])

            if len(current) == 1:
                reading = next(iter(current))
                assigned = {reading: total}
                basis = "当前8454仅一个读音；封闭集合内全量归入"
            else:
                unihan_total = sum(unihan_current.values())
                u_dom = dominant(unihan_current)
                c_dom = dominant(chai_all)
                if unihan_total < args.minimum_unihan_samples:
                    reasons.append(f"当前集合内Unihan样本少于{args.minimum_unihan_samples}")
                if u_dom is None:
                    reasons.append("当前集合内Unihan主读音不唯一或无样本")
                if c_dom is None:
                    reasons.append("Chai主读音不唯一或无正频率")
                if u_dom and c_dom and u_dom != c_dom:
                    reasons.append("Unihan与Chai主读音冲突")
                unihan_missing_not_explicit_zero = sorted(
                    key for key in missing_in_unihan if key not in chai_all or chai_all[key] != 0
                )
                if unihan_missing_not_explicit_zero:
                    reasons.append("Unihan缺音且Chai未明确零频:" + "/".join(unihan_missing_not_explicit_zero))
                if reasons:
                    assigned = {}
                else:
                    assigned = largest_remainder(total, unihan_current, current)
                    basis = "Unihan限制到当前集合后分配；缺失项经Chai明确为0"

            status = "新增定案" if assigned else "继续待复核"
            if assigned:
                for reading, frequency in assigned.items():
                    new_allocations[(char, reading)] += frequency
            audit_rows.append({
                "影响排名": int(row["影响排名"]),
                "汉字": char,
                "SUBTLEX单字总频": total,
                "当前8454集合": "/".join(sorted(current)),
                "Unihan全部频率": ";".join(f"{key}:{value}" for key, value in unihan_all.most_common()),
                "Unihan当前集合频率": ";".join(f"{key}:{value}" for key, value in unihan_current.most_common()),
                "Chai频率": ";".join(f"{key}:{value}" for key, value in chai_all.most_common()),
                "状态": status,
                "分配依据": basis,
                "分配结果": ";".join(f"{key}:{value}" for key, value in sorted(assigned.items())),
                "待复核原因": "；".join(reasons),
            })

    audit_rows.sort(key=lambda row: int(row["影响排名"]))
    audit_path = args.output_dir / "封闭读音集合定案审计.tsv"
    with audit_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit_rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(audit_rows)

    allocation_path = args.output_dir / "封闭读音集合新增定案.tsv"
    with allocation_path.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["汉字", "拼音", "新增定案频率", "状态"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for pair in sorted(new_allocations, key=lambda item: (-new_allocations[item], item[0], item[1])):
            writer.writerow({"汉字": pair[0], "拼音": pair[1], "新增定案频率": new_allocations[pair], "状态": "设计0029新增定案"})

    stage_rows: list[dict[str, object]] = []
    with args.stage_table.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            pair = (row["汉字"], row["拼音"])
            addition = new_allocations[pair]
            existing = int(row["阶段性合计频率"])
            stage_rows.append({
                "汉字": pair[0],
                "拼音": pair[1],
                "设计0026前阶段频率": existing,
                "封闭集合新增单字频率": addition,
                "封闭集合阶段合计频率": existing + addition,
                "状态": "阶段性候选；当前8454封闭；仍有待复核频率",
            })
    stage_rows.sort(key=lambda row: (-int(row["封闭集合阶段合计频率"]), str(row["汉字"]), str(row["拼音"])))
    stage_output = args.output_dir / "SUBTLEX阶段性分读音频率表_封闭读音版.tsv"
    with stage_output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(stage_rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(stage_rows)

    settled = [row for row in audit_rows if row["状态"] == "新增定案"]
    pending = [row for row in audit_rows if row["状态"] != "新增定案"]
    settled_frequency = sum(int(row["SUBTLEX单字总频"]) for row in settled)
    pending_frequency = sum(int(row["SUBTLEX单字总频"]) for row in pending)
    report = {
        "previously_pending_items": len(audit_rows),
        "newly_settled_items": len(settled),
        "remaining_pending_items": len(pending),
        "newly_settled_frequency": settled_frequency,
        "remaining_pending_frequency": pending_frequency,
        "newly_settled_ratio_of_previous_pending": settled_frequency / (settled_frequency + pending_frequency),
        "allocation_conservation": sum(new_allocations.values()) == settled_frequency,
        "top30_newly_settled": sum(row["状态"] == "新增定案" for row in audit_rows if int(row["影响排名"]) <= 30),
    }
    (args.output_dir / "封闭读音集合定案报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# 封闭读音集合继续定案报告",
        "",
        f"- 此前待复核：{len(audit_rows):,} 项",
        f"- 本轮新增定案：{len(settled):,} 项，频率 {settled_frequency:,}",
        f"- 仍待复核：{len(pending):,} 项，频率 {pending_frequency:,}",
        f"- 吃掉此前待复核频率：{report['newly_settled_ratio_of_previous_pending']:.2%}",
        f"- 前30项新增定案：{report['top30_newly_settled']}",
        f"- 分配守恒：{'是' if report['allocation_conservation'] else '否'}",
        "",
        "## 前30项中的本轮结果",
        "",
        "| 排名 | 字 | 当前集合 | 状态 | 分配／原因 |",
        "|---:|:---:|---|---|---|",
    ]
    for row in [item for item in audit_rows if int(item["影响排名"]) <= 30]:
        detail = row["分配结果"] if row["状态"] == "新增定案" else row["待复核原因"]
        lines.append(f"| {row['影响排名']} | {row['汉字']} | {row['当前8454集合']} | {row['状态']} | {detail} |")
    lines.extend(["", "本轮未新增任何读音，也未覆盖最终退火输入。", ""])
    (args.output_dir / "封闭读音集合定案报告.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
