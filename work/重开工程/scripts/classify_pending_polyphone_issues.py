#!/usr/bin/env python3
"""对待复核多音项按集合差异、主读音冲突和样本状态分层。"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def split_set(value: str) -> set[str]:
    return {item for item in value.split("/") if item}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--minimum-unihan-samples", type=int, default=100)
    args = parser.parse_args()

    output_rows: list[dict[str, object]] = []
    counts: Counter[str] = Counter()
    frequencies: Counter[str] = Counter()
    with args.decisions.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["状态"] == "已定":
                continue
            s_set = split_set(row["SUBTLEX去调候选"])
            c_set = split_set(row["当前8454候选"])
            u_set = {item.rsplit(":", 1)[0] for item in row["Unihan频率"].split(";") if item}
            possible_missing = (s_set | u_set) - c_set
            current_not_subtlex = c_set - s_set
            current_not_unihan = c_set - u_set
            categories: list[str] = []
            if possible_missing:
                categories.append("当前可能漏音")
            if current_not_subtlex:
                categories.append("当前含SUBTLEX未列读音")
            if current_not_unihan:
                categories.append("当前含Unihan未列读音")
            if not u_set:
                categories.append("Unihan未覆盖")
            elif int(row["Unihan样本总数"]) < args.minimum_unihan_samples:
                categories.append("Unihan小样本")
            if row["Unihan主读音"] and row["Chai主读音"] and row["Unihan主读音"] != row["Chai主读音"]:
                categories.append("主读音冲突")
            if not categories:
                categories.append("其他门槛未通过")

            frequency = int(row["SUBTLEX单字总频"])
            for category in categories:
                counts[category] += 1
                frequencies[category] += frequency
            output_rows.append({
                "影响排名": int(row["影响排名"]),
                "汉字": row["汉字"],
                "未分配频率": frequency,
                "SUBTLEX集合": "/".join(sorted(s_set)),
                "当前8454集合": "/".join(sorted(c_set)),
                "Unihan集合": "/".join(sorted(u_set)),
                "来源提示当前可能漏音": "/".join(sorted(possible_missing)),
                "当前已有但SUBTLEX未列": "/".join(sorted(current_not_subtlex)),
                "当前已有但Unihan未列": "/".join(sorted(current_not_unihan)),
                "Unihan主读音": row["Unihan主读音"],
                "Chai主读音": row["Chai主读音"],
                "Unihan样本总数": row["Unihan样本总数"],
                "问题分类": "；".join(categories),
                "原拒绝原因": row["原因"],
            })

    output_rows.sort(key=lambda row: (int(row["影响排名"]), str(row["汉字"])))
    fields = list(output_rows[0])
    output_path = args.output_dir / "多音待复核问题分层.tsv"
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(output_rows)

    missing_rows = [row for row in output_rows if row["来源提示当前可能漏音"]]
    missing_path = args.output_dir / "当前8454可能漏音候选.tsv"
    with missing_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(missing_rows)

    report = {
        "pending_items": len(output_rows),
        "pending_frequency": sum(int(row["未分配频率"]) for row in output_rows),
        "possible_missing_items": len(missing_rows),
        "possible_missing_frequency": sum(int(row["未分配频率"]) for row in missing_rows),
        "category_item_counts_nonexclusive": dict(counts),
        "category_frequency_nonexclusive": dict(frequencies),
    }
    (args.output_dir / "多音待复核问题分层.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# 多音待复核问题分层",
        "",
        f"- 待复核：{report['pending_items']:,} 项，频率 {report['pending_frequency']:,}",
        f"- 来源提示当前可能漏音：{report['possible_missing_items']:,} 项，频率 {report['possible_missing_frequency']:,}",
        "- 分类允许重叠，因此分类计数不能直接相加。",
        "",
        "## 分类统计",
        "",
    ]
    for category, count in counts.most_common():
        lines.append(f"- {category}：{count:,} 项，涉及频率 {frequencies[category]:,}")
    lines.extend(["", "## 最高影响的可能漏音候选", "", "| 排名 | 字 | 可能漏音 | 当前 | 来源集合 | 频率 |", "|---:|:---:|---|---|---|---:|"])
    for row in missing_rows[:30]:
        lines.append(
            f"| {row['影响排名']} | {row['汉字']} | {row['来源提示当前可能漏音']} | {row['当前8454集合']} | S={row['SUBTLEX集合']}；U={row['Unihan集合']} | {int(row['未分配频率']):,} |"
        )
    lines.extend(["", "“可能漏音”只是待查候选，不是增音决定。", ""])
    (args.output_dir / "多音待复核问题分层.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
