#!/usr/bin/env python3
"""按0.8.6口径重扫夜莺0.8.5第二届256张卡。"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path


def effective_full_count(path: Path) -> int:
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        _, _, full_rank, actual, _ = line.split("\t")
        if int(full_rank) > 0 and len(actual) > 2:
            count += 1
    return count


def dominates(a: dict, b: dict) -> bool:
    keys_low = ("pair", "large", "small", "micro", "pinky")
    no_worse = all(a[k] <= b[k] for k in keys_low) and a["separation"] >= b["separation"]
    better = any(a[k] < b[k] for k in keys_low) or a["separation"] > b["separation"]
    return no_worse and better


def pct(value: float) -> str:
    return f"{value * 100:.3f}%"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tournament", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--three-loss", type=int, default=20)
    parser.add_argument("--duplicate-extra", type=int, default=20)
    args = parser.parse_args()

    rows = []
    for group in range(1, 17):
        directory = args.tournament / f"group_{group:02d}"
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        core = json.loads((directory / "core_metrics.json").read_text(encoding="utf-8"))
        hand = json.loads((directory / "handfeel.json").read_text(encoding="utf-8"))["candidates"]
        cards = {f"G{group}C{int(card['card']):02d}": card for card in manifest["cards"]}
        for name, item in core.items():
            h = hand[name]["1500"]
            rows.append({
                "name": name,
                "three": int(item["layers"]["6000"]["three_code_count"]),
                "front300": int(item["layers"]["300"]["effective_full_duplication"]),
                "front1500": int(item["front1500_effective_full_duplication"]),
                "full_dup_rate": float(item["full_duplication"]),
                "short_dup_rate": float(item["short_duplication"]),
                "pair": float(item["short_pair_equivalence"]),
                "large": float(item["short_large_cross"]),
                "small": float(item["short_small_cross"]),
                "micro": float(h["single_finger_move"]["event_rate"]),
                "pinky": float(h["pinky_linkage"]["event_rate"]),
                "separation": float(h["phonetic_shape_hand_separation"]["separation_rate"]),
                "code_path": str((Path(cards[name]["output_directory"]) / "code.txt").resolve()),
            })
    baseline = next(row for row in rows if row["name"] == "G8C12")
    baseline["total_effective"] = effective_full_count(Path(baseline["code_path"]))
    coarse = [row for row in rows if row["front300"] == 0 and
              row["three"] >= baseline["three"] - args.three_loss]
    for row in coarse:
        row["total_effective"] = effective_full_count(Path(row["code_path"]))
    eligible = [row for row in coarse if row["total_effective"] <=
                baseline["total_effective"] + args.duplicate_extra]

    scales = {"pair": .005, "large": .002, "small": .003,
              "micro": .004, "pinky": .006, "separation": .05}
    for row in eligible:
        row["hand_improvements"] = sum([
            row["pair"] < baseline["pair"], row["large"] < baseline["large"],
            row["small"] < baseline["small"], row["micro"] < baseline["micro"],
            row["pinky"] < baseline["pinky"], row["separation"] > baseline["separation"],
        ])
        row["distance"] = math.sqrt(sum(
            ((row[key] - baseline[key]) / scales[key]) ** 2 for key in scales))
    eligible.sort(key=lambda row: (row["distance"], -row["hand_improvements"], row["name"]))
    pareto = [row for row in eligible if not any(dominates(other, row) for other in eligible if other is not row)]
    pareto.sort(key=lambda row: (row["distance"], row["name"]))

    result = {"schema_version": 1, "baseline": baseline, "cards": len(rows),
              "coarse_eligible": len(coarse), "eligible": len(eligible),
              "three_loss_limit": args.three_loss, "duplicate_extra_limit": args.duplicate_extra,
              "pareto": pareto, "nearest": eligible[:20], "eligible_all": eligible}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def table(items: list[dict]) -> list[str]:
        lines = ["| 候选 | 三码 | 总有效重码 | 前1500重码 | 当量 | 大跨 | 小跨 | 微移 | 小指联动 | 换手 | 优于基线项数 | 距离 |",
                 "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for r in items:
            lines.append(f"| {r['name']} | {r['three']} | {r['total_effective']} | {r['front1500']} | "
                         f"{r['pair']:.6f} | {pct(r['large'])} | {pct(r['small'])} | {pct(r['micro'])} | "
                         f"{pct(r['pinky'])} | {pct(r['separation'])} | {r['hand_improvements']} | {r['distance']:.3f} |")
        return lines

    lines = ["# 夜莺0.8.5第二届256卡：0.8.6口径帕累托扫描", "",
             f"- 基线：G8C12；前6000三码{baseline['three']}；全体有效重码字{baseline['total_effective']}。",
             f"- 门禁：前300有效重码为0；三码最多损失{args.three_loss}；总有效重码最多增加{args.duplicate_extra}。",
             f"- 256卡中，三码/前300粗筛剩{len(coarse)}张；加入总重码预算后剩{len(eligible)}张。", "",
             "## 手感六维帕累托前沿", "", *table(pareto), "",
             "## 距离G8C12最近的20张", "", *table(eligible[:20]), "",
             "距离仅用于近邻排序：当量、大跨、小跨、微移、小指联动、换手分别按0.005、0.2pp、0.3pp、0.4pp、0.6pp、5pp归一化；不作为发布总分。", ""]
    args.output_md.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"cards": len(rows), "coarse": len(coarse), "eligible": len(eligible),
                      "pareto": len(pareto)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
