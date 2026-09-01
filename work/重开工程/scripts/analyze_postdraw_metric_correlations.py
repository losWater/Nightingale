#!/usr/bin/env python3
"""分析16张正式卡的新旧手感指标Pearson相关性。"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("Pearson输入长度非法")
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    dx, dy = [x - mx for x in xs], [y - my for y in ys]
    denominator = math.sqrt(sum(x * x for x in dx) * sum(y * y for y in dy))
    return sum(x * y for x, y in zip(dx, dy)) / denominator if denominator else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--extras", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()
    core = json.loads(args.core.read_text(encoding="utf-8"))
    extras = json.loads(args.extras.read_text(encoding="utf-8"))
    core_runs = core.get("runs") or core.get("candidates") or core
    extra_runs = extras["candidates"]
    names = sorted(set(core_runs) & set(extra_runs))
    if len(names) != 16:
        raise ValueError(f"预期16张共同候选，实际{len(names)}")

    series: dict[str, list[float]] = {
        "三码6000": [], "简码当量": [], "大跨": [], "小跨": [],
        "全码重码": [], "简码重码": [], "前1500全码重": [], "左右手偏差": [],
        "单指微移1500": [], "小指联动1500": [], "音形分离1500": [],
    }
    per_card = {}
    for name in names:
        c, e = core_runs[name], extra_runs[name]["1500"]
        values = {
            "三码6000": float(c["layers"]["6000"]["three_code_count"]),
            "简码当量": float(c["short_pair_equivalence"]),
            "大跨": float(c["short_large_cross"]),
            "小跨": float(c["short_small_cross"]),
            "全码重码": float(c["full_duplication"]),
            "简码重码": float(c["short_duplication"]),
            "前1500全码重": float(c["front1500_full_duplication"]),
            "左右手偏差": abs(float(c["heat_front1500"]["left"]) - 0.5),
            "单指微移1500": float(e["single_finger_move"]["event_rate"]),
            "小指联动1500": float(e["pinky_linkage"]["event_rate"]),
            "音形分离1500": float(e["phonetic_shape_hand_separation"]["separation_rate"]),
        }
        per_card[name] = values
        for key, value in values.items():
            series[key].append(value)

    keys = list(series)
    matrix = {a: {b: pearson(series[a], series[b]) for b in keys} for a in keys}
    old_keys = keys[:8]
    focus = sorted(((key, matrix["音形分离1500"][key]) for key in old_keys),
                   key=lambda item: abs(item[1]))
    ranges = {key: {"min": min(values), "max": max(values)} for key, values in series.items()}
    result = {"schema_version": 1, "design": "0057", "n": len(names), "cards": names,
              "per_card": per_card, "ranges": ranges, "pearson": matrix,
              "phonetic_shape_vs_old_by_abs": focus}
    args.output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = ["# 十六卡附加手感指标相关性", "",
             "- 样本：n=16（0054全部正式卡，含硬门禁淘汰卡）",
             "- 指法：B=右手食指",
             "- Pearson只描述本轮候选的线性共变，不代表因果或严格独立。", "",
             "## 音形分离率与旧指标", "",
             "| 旧指标 | Pearson r | |r| |", "|---|---:|---:|"]
    for key, value in focus:
        lines.append(f"| {key} | {value:+.3f} | {abs(value):.3f} |")
    lines += ["", "## 三项新指标范围（前1500）", "",
              "| 指标 | 最低 | 最高 | 极差 |", "|---|---:|---:|---:|"]
    for key in ("单指微移1500", "小指联动1500", "音形分离1500"):
        low, high = ranges[key]["min"], ranges[key]["max"]
        lines.append(f"| {key} | {low*100:.3f}% | {high*100:.3f}% | {(high-low)*100:.3f}pp |")
    lines += ["", "## 完整相关矩阵", "",
              "| 指标 | " + " | ".join(keys) + " |",
              "|---|" + "---:|" * len(keys)]
    for a in keys:
        lines.append("| " + a + " | " + " | ".join(f"{matrix[a][b]:+.3f}" for b in keys) + " |")
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "n": len(names), "focus": focus}, ensure_ascii=False))


if __name__ == "__main__":
    main()
