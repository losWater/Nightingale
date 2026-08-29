# -*- coding: utf-8 -*-
"""汇总终局 B 长跑的训练指标、隐藏词位泛化与 Pareto 候选。"""
from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parents[1]
WORK = BASE / "work"
FULL = re.compile(r"一字全码［选重率：([\d.]+)%；组合当量：([\d.]+)；1500 选重：(\d+)；.*?3500 选重：(\d+)；.*?6000 选重：(\d+)；")
SHORT = re.compile(r"一字简码［选重率：([\d.]+)%；组合当量：([\d.]+)；1500 选重：(\d+)；.*?1500 三键：(\d+)；3500 选重：(\d+)；.*?3500 三键：(\d+)；")
CROSS = re.compile(r"字词交叉［硬碰撞：(\d+)；软碰撞当量：([\d.]+)；")


def read_tsv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def word_weight(rank):
    return 1.0 if rank <= 2000 else 0.5 if rank <= 10000 else 0.2 if rank <= 30000 else 0.05


def dominates(a, b):
    minimize = ("full3500", "full6000", "short3500", "full_pair", "short_pair", "hidden_risk")
    maximize = ("three1500", "three3500")
    no_worse = all(a[k] <= b[k] for k in minimize) and all(a[k] >= b[k] for k in maximize)
    better = any(a[k] < b[k] for k in minimize) or any(a[k] > b[k] for k in maximize)
    return no_worse and better


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("run", type=Path); ap.add_argument("validation", type=Path)
    args = ap.parse_args()
    validation = {row["code"]: row for row in read_tsv(args.validation)}
    elements = yaml.safe_load((WORK / "analysis_elements.yaml").read_text(encoding="utf-8"))
    order = sorted(range(len(elements)), key=lambda i: -int(elements[i].get("频率", 0)))
    output_dir = next(args.run.glob("output-*"))
    rows = []
    for metric_path in output_dir.glob("*/metric.txt"):
        text = metric_path.read_text(encoding="utf-8")
        full, short, cross = FULL.search(text), SHORT.search(text), CROSS.search(text)
        code_path = metric_path.parent / "code.txt"
        codes = [line.split("\t")[1] for line in code_path.read_text(encoding="utf-8").splitlines()]
        hits = {1500: 0, 3500: 0, 5000: 0}; weighted = 0.0; distinct = Counter()
        for rank, index in enumerate(order[:5000], 1):
            target = validation.get(codes[index])
            if target is None: continue
            distinct[codes[index]] += 1
            for top in hits:
                if rank <= top: hits[top] += 1
            factor = 1.0 if rank <= 1500 else 0.5 if rank <= 3500 else 0.2
            weighted += factor * word_weight(int(target["two_top_rank"]))
        row = {"thread": int(metric_path.parent.name), "full_pair": float(full[2]),
               "full1500": int(full[3]), "full3500": int(full[4]), "full6000": int(full[5]),
               "short_pair": float(short[2]), "short1500": int(short[3]), "three1500": int(short[4]),
               "short3500": int(short[5]), "three3500": int(short[6]), "hard": int(cross[1]),
               "train_soft": float(cross[2]), "hidden1500": hits[1500], "hidden3500": hits[3500],
               "hidden5000": hits[5000], "hidden_slots": len(distinct), "hidden_risk": round(weighted, 6),
               "directory": str(metric_path.parent)}
        row["valid"] = int(row["hard"] == row["full1500"] == row["short1500"] == 0)
        rows.append(row)
    valid = [row for row in rows if row["valid"]]
    for row in rows:
        row["pareto"] = int(row in valid and not any(dominates(other, row) for other in valid if other is not row))
    rows.sort(key=lambda row: (-row["valid"], -row["pareto"], row["hidden_risk"], row["full3500"]))
    fields = ["thread", "valid", "pareto", "hard", "full1500", "full3500", "full6000",
              "short1500", "short3500", "three1500", "three3500", "full_pair", "short_pair",
              "train_soft", "hidden1500", "hidden3500", "hidden5000", "hidden_slots", "hidden_risk", "directory"]
    with (args.run / "终局候选分析.tsv").open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=fields, delimiter="\t"); wr.writeheader(); wr.writerows(rows)
    print(f"all={len(rows)} valid={len(valid)} pareto={sum(row['pareto'] for row in rows)}")
    for row in rows: print(row)


if __name__ == "__main__": main()
