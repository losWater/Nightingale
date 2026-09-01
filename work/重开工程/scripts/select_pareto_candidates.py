#!/usr/bin/env python3
"""从核心指标JSON筛选Pareto候选并展开具体全码重码。"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import yaml


def objectives(row: dict) -> tuple[float, ...]:
    return (
        -float(row["layers"]["6000"]["three_code_count"]),
        float(row["short_pair_equivalence"]),
        float(row["short_large_cross"]),
        float(row["short_small_cross"]),
        float(row["full_duplication"]),
        float(row["short_duplication"]),
        float(row["front1500_full_duplication"]),
        abs(float(row["heat_front1500"]["left"]) - 0.5),
    )


def dominates(a: dict, b: dict) -> bool:
    av, bv = objectives(a), objectives(b)
    return all(x <= y for x, y in zip(av, bv)) and any(x < y for x, y in zip(av, bv))


def load_codes(directory: Path, elements: list[dict]) -> list[tuple[int, str, str]]:
    rows = [line.split("\t") for line in (directory / "code.txt").read_text(encoding="utf-8").splitlines()]
    if len(rows) != len(elements):
        raise ValueError(f"{directory}: code与elements行数不一致")
    records = []
    for index, (item, cols) in enumerate(zip(elements, rows)):
        if len(cols) < 4 or cols[0] != str(item["词"]):
            raise ValueError(f"{directory}: 第{index + 1}行身份错位")
        order = item.get("排序序号")
        records.append((index, int(item["频率"]), order, cols[0], cols[1]))
    if any(x[2] is not None for x in records):
        records.sort(key=lambda x: (x[2] if x[2] is not None else 2**63 - 1, x[0]))
    else:
        records.sort(key=lambda x: (-x[1], x[0]))
    return [(x[0], x[3], x[4]) for x in records]


def collisions(records: list[tuple[int, str, str]], top: int) -> list[dict]:
    groups: dict[str, list[str]] = {}
    for _, char, code in records[:top]:
        groups.setdefault(code, []).append(char)
    return [
        {"code": code, "characters": chars, "extra_candidates": len(chars) - 1}
        for code, chars in groups.items() if len(chars) > 1
    ]


def pct(value: float) -> str:
    return f"{value * 100:.3f}%"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--elements", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()
    all_rows = json.loads(args.metrics.read_text(encoding="utf-8"))
    elements = yaml.safe_load(args.elements.read_text(encoding="utf-8"))
    candidates = {name: row for name, row in all_rows.items() if name != "基线"}
    eligible = {}
    rejected = {}
    for name, row in candidates.items():
        values = objectives(row)
        if not all(math.isfinite(x) for x in values):
            raise ValueError(f"{name}含非有限指标")
        bad = int(row["layers"]["300"]["effective_full_duplication"])
        if bad:
            rejected[name] = f"前300有效全码重码={bad}"
        else:
            eligible[name] = row
    pareto = {
        name: row for name, row in eligible.items()
        if not any(dominates(other, row) for other_name, other in eligible.items() if other_name != name)
    }
    output = {"schema_version": 1, "eligible": sorted(eligible), "rejected": rejected,
              "pareto": {}}
    for name, row in pareto.items():
        records = load_codes(Path(row["directory"]), elements)
        collision_sets = {top: collisions(records, top) for top in (300, 500, 1500)}
        for top, found in collision_sets.items():
            independently_counted = sum(x["extra_candidates"] for x in found)
            expected = (int(row["layers"][str(top)]["full_duplication"])
                        if top != 1500 else int(row["front1500_full_duplication"]))
            if independently_counted != expected:
                raise ValueError(
                    f"{name}前{top}全码重码独立复算{independently_counted} != metric {expected}"
                )
        output["pareto"][name] = {
            "metrics": row,
            "objectives_minimize": list(objectives(row)),
            "front300_full_collisions": collision_sets[300],
            "front500_full_collisions": collision_sets[500],
            "front1500_full_collisions": collision_sets[1500],
        }
    args.output_json.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 长链Pareto候选与具体重码", "",
             f"- 合资格：{len(eligible)}；硬门禁淘汰：{len(rejected)}；Pareto：{len(pareto)}。", "",
             "| 候选 | 三码6000 | 简码当量 | 大跨 | 小跨 | 全码重码率 | 简码重码率 | 前1500重 | 左手 |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name, row in pareto.items():
        lines.append(f"| {name} | {row['layers']['6000']['three_code_count']} | {row['short_pair_equivalence']:.6f} | {pct(row['short_large_cross'])} | {pct(row['short_small_cross'])} | {pct(row['full_duplication'])} | {pct(row['short_duplication'])} | {row['front1500_full_duplication']} | {pct(row['heat_front1500']['left'])} |")
    for name, item in output["pareto"].items():
        lines += ["", f"## {name}", "",
                  "前500：" + ("；".join(f"`{x['code']}` {'/'.join(x['characters'])}" for x in item["front500_full_collisions"]) or "无"), "",
                  "前1500：" + ("；".join(f"`{x['code']}` {'/'.join(x['characters'])}" for x in item["front1500_full_collisions"]) or "无"), ""]
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
