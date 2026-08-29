# -*- coding: utf-8 -*-
"""汇总 A/B 正式退火的训练指标与公共隐藏验证指标。"""
from __future__ import annotations

import argparse
import csv
import re
import statistics
from pathlib import Path


FULL = re.compile(r"一字全码［选重率：([\d.]+)%；组合当量：([\d.]+)；1500 选重：(\d+)；.*?3500 选重：(\d+)；.*?6000 选重：(\d+)；")
SHORT = re.compile(r"一字简码［选重率：([\d.]+)%；组合当量：([\d.]+)；1500 选重：(\d+)；.*?1500 三键：(\d+)；3500 选重：(\d+)；.*?3500 三键：(\d+)；")
CROSS = re.compile(r"字词交叉［硬碰撞：(\d+)；软碰撞当量：([\d.]+)；")


def read_tsv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def metric(path):
    text = path.read_text(encoding="utf-8")
    full, short, cross = FULL.search(text), SHORT.search(text), CROSS.search(text)
    if not all((full, short, cross)): raise ValueError(path)
    return {"full_pair": float(full[2]), "full1500": int(full[3]), "full3500": int(full[4]),
            "full6000": int(full[5]), "short_pair": float(short[2]), "short1500": int(short[3]),
            "three1500": int(short[4]), "short3500": int(short[5]), "three3500": int(short[6]),
            "hard": int(cross[1]), "train_soft": float(cross[2])}


def med(rows, key): return round(statistics.median(row[key] for row in rows), 6)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("suite", type=Path); args = ap.parse_args()
    hidden = {(row["variant"], int(row["thread"])): row for row in read_tsv(args.suite / "公共隐藏验证结果.tsv")
              if row["run"] == "formal"}
    all_rows = []
    for variant in ("A_frequency15000", "B_core10000_novel5000"):
        root = args.suite / variant / "formal_12x100000"
        for path in root.glob("output-*/*/metric.txt"):
            row = metric(path); thread = int(path.parent.name)
            row.update({"variant": variant, "thread": thread,
                        "hidden1500": int(hidden[(variant, thread)]["hidden_hit_1500"]),
                        "hidden3500": int(hidden[(variant, thread)]["hidden_hit_3500"]),
                        "hidden5000": int(hidden[(variant, thread)]["hidden_hit_5000"]),
                        "hidden_risk": float(hidden[(variant, thread)]["hidden_weighted_risk"]),
                        "directory": str(path.parent)})
            row["valid"] = int(row["hard"] == 0 and row["full1500"] == 0 and row["short1500"] == 0)
            all_rows.append(row)
    fields = ["variant", "thread", "valid", "hard", "full1500", "full3500", "full6000",
              "short1500", "short3500", "three1500", "three3500", "full_pair", "short_pair",
              "train_soft", "hidden1500", "hidden3500", "hidden5000", "hidden_risk", "directory"]
    with (args.suite / "正式AB结果.tsv").open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=fields, delimiter="\t"); wr.writeheader(); wr.writerows(all_rows)
    for variant in ("A_frequency15000", "B_core10000_novel5000"):
        rows = [r for r in all_rows if r["variant"] == variant]
        valid = [r for r in rows if r["valid"]]
        print(variant, "all", len(rows), "valid", len(valid))
        basis = valid or rows
        for key in ("full3500", "full6000", "short3500", "three1500", "three3500",
                    "full_pair", "short_pair", "train_soft", "hidden1500", "hidden3500",
                    "hidden5000", "hidden_risk"):
            print(f"  {key}: median={med(basis,key)} best={'max' if key.startswith('three') else 'min'}="
                  f"{(max if key.startswith('three') else min)(r[key] for r in basis)}")
        best = min(basis, key=lambda r: (r["hidden_risk"], r["full3500"], r["full6000"]))
        print("  hidden_best", best)


if __name__ == "__main__": main()
