# -*- coding: utf-8 -*-
"""用共同隐藏词位评估 A/B 输出；验证集不参与退火。"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parents[1]
WORK = BASE / "work"


def read_tsv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def word_weight(rank):
    if rank <= 2000: return 1.0
    if rank <= 10000: return 0.5
    if rank <= 30000: return 0.2
    return 0.05


def char_factor(rank):
    return 1.0 if rank <= 1500 else 0.5 if rank <= 3500 else 0.2 if rank <= 5000 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("suite", type=Path)
    args = ap.parse_args()
    validation = {row["code"]: row for row in read_tsv(args.suite / "公共隐藏验证位.tsv")}
    elements = yaml.safe_load((WORK / "analysis_elements.yaml").read_text(encoding="utf-8"))
    order = sorted(range(len(elements)), key=lambda i: -int(elements[i].get("频率", 0)))
    char_rank = {index: rank for rank, index in enumerate(order, 1)}
    results = []
    candidates = []
    for variant in ("A_frequency15000", "B_core10000_novel5000"):
        candidates.extend((variant, code_path) for code_path in (args.suite / variant).rglob("output-*/*/code.txt"))
    baseline = WORK / "snapshots" / "usable_layout_夕M长J_20260825" / "code.txt"
    if baseline.exists():
        candidates.append(("archived_usable", baseline))
    for variant, code_path in candidates:
            codes = [line.split("\t")[1] for line in code_path.read_text(encoding="utf-8").splitlines()]
            if len(codes) != len(elements):
                raise ValueError(f"{code_path}: {len(codes)} != {len(elements)}")
            hit_entries = Counter(); weighted = 0.0
            by_tier = {1500: 0, 3500: 0, 5000: 0}
            for index in order[:5000]:
                code = codes[index]
                row = validation.get(code)
                if row is None: continue
                rank = char_rank[index]
                hit_entries[code] += 1
                for top in by_tier:
                    if rank <= top: by_tier[top] += 1
                weighted += char_factor(rank) * word_weight(int(row["two_top_rank"]))
            results.append({
                "variant": variant,
                "run": "baseline" if variant == "archived_usable" else "formal" if "formal_" in str(code_path) else "smoke",
                "thread": -1 if variant == "archived_usable" else int(code_path.parent.name),
                "hidden_hit_1500": by_tier[1500], "hidden_hit_3500": by_tier[3500],
                "hidden_hit_5000": by_tier[5000], "hidden_distinct_slots": len(hit_entries),
                "hidden_weighted_risk": round(weighted, 6), "directory": str(code_path.parent),
            })
    results.sort(key=lambda row: (row["hidden_weighted_risk"], row["variant"], row["thread"]))
    out = args.suite / "公共隐藏验证结果.tsv"
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]), delimiter="\t")
        writer.writeheader(); writer.writerows(results)
    for row in results: print(row)


if __name__ == "__main__":
    main()
