#!/usr/bin/env python3
"""汇总新工程退火冒烟的核心指标；严格拒绝缺失和非有限数值。"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

import yaml


LAYERS = (300, 500, 1674, 3527, 6000)


def finite(value, label: str) -> float:
    if value is None:
        raise ValueError(f"{label}为null")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label}不是有限数：{value!r}")
    return number


def tiers(group: dict) -> dict[int, dict]:
    return {int(item["top"]): item for item in group["tiers"]}


def level3(item: dict) -> int:
    return int(next((x["frequency"] for x in item.get("levels", []) if x["length"] == 3), 0))


def load_codes(directory: Path, elements: list[dict]) -> list[tuple[str, str, str, int]]:
    raw = [line.split("\t") for line in (directory / "code.txt").read_text(encoding="utf-8").splitlines()]
    if len(raw) != len(elements):
        raise ValueError(f"{directory}: code/elements行数不一致")
    records = []
    for index, (item, row) in enumerate(zip(elements, raw)):
        if len(row) < 4 or row[0] != str(item["词"]):
            raise ValueError(f"{directory}: 第{index + 1}行身份错位")
        records.append((index, item, (row[0], row[1], row[3], int(item["频率"]))))
    if any(item.get("排序序号") is not None for _, item, _ in records):
        records.sort(key=lambda x: (x[1].get("排序序号", 2**63 - 1), x[0]))
    else:
        records.sort(key=lambda x: (-x[2][3], x[0]))
    return [x[2] for x in records]


def heat(records, top=1500) -> dict[str, float]:
    all_keys, third = Counter(), Counter()
    all_total = third_total = 0
    for _, _, code, freq in records[:top]:
        for key in code:
            all_keys[key] += freq
            all_total += freq
        if len(code) >= 3:
            third[code[2]] += freq
            third_total += freq
    if not all_total or not third_total:
        raise ValueError("热力分母为0")
    return {
        "left": sum(all_keys[x] for x in "qwertasdfgzxcvb") / all_total,
        "right": sum(all_keys[x] for x in "yuiophjklnm") / all_total,
        "zx_all": (all_keys["z"] + all_keys["x"]) / all_total,
        "fh_all": (all_keys["f"] + all_keys["h"]) / all_total,
        "zx_third": (third["z"] + third["x"]) / third_total,
        "fh_third": (third["f"] + third["h"]) / third_total,
    }


def load_run(spec: str, elements: list[dict]) -> tuple[str, dict]:
    name, sep, raw = spec.partition("=")
    if not sep:
        raise ValueError("运行参数必须为 名称=目录")
    directory = Path(raw)
    data = json.loads((directory / "metric.json").read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError(f"{name}: metric schema不是1")
    metric = data["metric"]
    full, short = metric["characters_full"], metric["characters_short"]
    ft, st = tiers(full), tiers(short)
    required = set(LAYERS) | {1500}
    if not required <= set(ft) or not required <= set(st):
        raise ValueError(f"{name}: 缺少分层 {sorted(required - (set(ft) & set(st)))}")
    result = {
        "score": finite(data["score"], f"{name}.score"),
        "full_duplication": finite(full["duplication"], f"{name}.全码重码率"),
        "effective_full_duplication": finite(full["effective_duplication"], f"{name}.有效全码重码率"),
        "short_duplication": finite(short["duplication"], f"{name}.简码重码率"),
        "short_pair_equivalence": finite(short["pair_equivalence"], f"{name}.简码组合当量"),
        "short_large_cross": finite(short["fingering"][1], f"{name}.简码大跨"),
        "short_small_cross": finite(short["fingering"][2], f"{name}.简码小跨"),
        "front1500_full_duplication": int(ft[1500]["duplication"]),
        "front1500_effective_full_duplication": int(ft[1500]["effective_duplication"]),
        "layers": {},
        "heat_front1500": heat(load_codes(directory, elements)),
        "directory": str(directory.resolve()),
    }
    for top in LAYERS:
        row = {
            "three_code_count": level3(st[top]),
            "three_code_rate": level3(st[top]) / top,
            "short_duplication": int(st[top]["duplication"]),
            "full_duplication": int(ft[top]["duplication"]),
            "effective_full_duplication": int(ft[top]["effective_duplication"]),
        }
        if top != 6000:
            row["short_large_cross"] = finite(st[top]["weighted_fingering"][1], f"{name}.{top}.大跨")
            row["short_small_cross"] = finite(st[top]["weighted_fingering"][2], f"{name}.{top}.小跨")
        result["layers"][str(top)] = row
    # 递归确认最终摘要没有漏过NaN。
    def check(value, path="root"):
        if isinstance(value, dict):
            for key, child in value.items(): check(child, f"{path}.{key}")
        elif isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"{path}不是有限数")
    check(result)
    return name, result


def pct(value: float) -> str:
    return f"{value * 100:.3f}%"


def render(runs: dict[str, dict]) -> str:
    names = list(runs)
    out = ["# 夜莺0.8新输入退火冒烟核心指标", "", "## 总览", "",
           "| 指标 | " + " | ".join(names) + " |",
           "|---|" + "---|" * len(names)]
    rows = [
        ("总分", "score", lambda x: f"{x:.6f}"),
        ("全码重码率", "full_duplication", pct),
        ("有效全码重码率", "effective_full_duplication", pct),
        ("简码重码率", "short_duplication", pct),
        ("简码组合当量", "short_pair_equivalence", lambda x: f"{x:.6f}"),
        ("简码大跨", "short_large_cross", pct),
        ("简码小跨", "short_small_cross", pct),
        ("前1500全码重", "front1500_full_duplication", str),
        ("前1500有效全码重", "front1500_effective_full_duplication", str),
    ]
    for label, key, fmt in rows:
        out.append(f"| {label} | " + " | ".join(fmt(runs[n][key]) for n in names) + " |")
    out += ["", "## 固定分层", ""]
    for name in names:
        out += [f"### {name}", "", "| 层 | 三码 | 三码率 | 简码重 | 全码重 | 有效全码重 | 简码大跨 | 简码小跨 |",
                "|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for top in LAYERS:
            row = runs[name]["layers"][str(top)]
            out.append(f"| {top} | {row['three_code_count']} | {pct(row['three_code_rate'])} | {row['short_duplication']} | {row['full_duplication']} | {row['effective_full_duplication']} | " +
                       (f"{pct(row['short_large_cross'])} | {pct(row['short_small_cross'])} |" if top != 6000 else "— | — |"))
        h = runs[name]["heat_front1500"]
        out += ["", f"前1500热力：左/右 {pct(h['left'])}/{pct(h['right'])}；z+x全部 {pct(h['zx_all'])}；f+h全部 {pct(h['fh_all'])}；第三键z+x {pct(h['zx_third'])}；第三键f+h {pct(h['fh_third'])}。", ""]
    return "\n".join(out) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--elements", type=Path, required=True)
    parser.add_argument("--run", action="append", required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()
    elements = yaml.safe_load(args.elements.read_text(encoding="utf-8"))
    runs = dict(load_run(spec, elements) for spec in args.run)
    args.output_json.write_text(json.dumps(runs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(render(runs), encoding="utf-8")


if __name__ == "__main__":
    main()
