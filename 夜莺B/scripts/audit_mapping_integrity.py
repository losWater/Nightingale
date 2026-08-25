# -*- coding: utf-8 -*-
"""检查最终键位映射的附属引用完整性与五笔画家族。"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import yaml


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("config", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    mapping = yaml.safe_load(args.config.read_text(encoding="utf-8"))["form"]["mapping"]
    dangling, cycles = [], []
    owners = defaultdict(list)
    for element in mapping:
        seen, current = set(), element
        while isinstance(mapping.get(str(current)), dict):
            if str(current) in seen:
                cycles.append(element)
                break
            seen.add(str(current))
            current = mapping[str(current)]["element"]
        if str(current) not in mapping:
            dangling.append((element, current))
        else:
            owners[str(current)].append(element)
    names = {"1": "横", "2": "竖", "3": "撇", "4": "点", "5": "折"}
    report = ["# 最终映射结构审计", "",
              f"- 映射元素：{len(mapping)}",
              f"- 悬空引用：{len(dangling)}",
              f"- 循环引用：{len(cycles)}", "",
              "## 五笔画家族", "",
              "| 家族 | 最终键 | 成员数 | 成员 |", "|---|---|---:|---|"]
    for stroke, label in names.items():
        members = owners[stroke]
        report.append(f"| {label} | {str(mapping[stroke]).upper()} | {len(members)} | {'、'.join(members)} |")
    if dangling:
        report += ["", "## 悬空明细", "", *[f"- {a} → {b}" for a, b in dangling]]
    if cycles:
        report += ["", "## 循环明细", "", *[f"- {x}" for x in cycles]]
    text = "\n".join(report) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(f"mapping={len(mapping)} dangling={len(dangling)} cycles={len(cycles)}")
    if args.out:
        print(args.out)


if __name__ == "__main__":
    main()
