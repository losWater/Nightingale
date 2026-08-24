# -*- coding: utf-8 -*-
"""合并二字全拼词与四字简拼词，生成四码位级目标集。"""
import csv
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
LEX = BASE / "work" / "lexicon"

def read_tsv(name):
    with (LEX / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))

def main():
    two = read_tsv("二字词_精选60000.tsv")
    four = read_tsv("四字简词_精选.tsv")
    slots = defaultdict(lambda: {"two": [], "four": []})
    for rank, row in enumerate(two, 1):
        slots[row["code"]]["two"].append((rank, row["word"]))
    for rank, row in enumerate(four, 1):
        slots[row["code"]]["four"].append((rank, row["word"]))

    rows = []
    for code, groups in slots.items():
        tw, fw = groups["two"], groups["four"]
        rows.append({
            "code": code,
            "has_two": int(bool(tw)), "has_four": int(bool(fw)),
            "two_count": len(tw), "four_count": len(fw),
            "two_top_rank": min((r for r, _ in tw), default=""),
            "four_top_rank": min((r for r, _ in fw), default=""),
            "two_words": " ".join(w for _, w in tw),
            "four_words": " ".join(w for _, w in fw),
        })
    rows.sort(key=lambda r: (-r["has_two"], int(r["two_top_rank"] or 10**9),
                             int(r["four_top_rank"] or 10**9), r["code"]))
    fields = list(rows[0])
    with (LEX / "目标词库_四码位.tsv").open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        wr.writeheader(); wr.writerows(rows)

    two_slots = sum(r["has_two"] for r in rows)
    four_slots = sum(r["has_four"] for r in rows)
    overlap = sum(r["has_two"] and r["has_four"] for r in rows)
    report = ["# 目标词库四码位合并报告", "",
              f"- 二字词：{len(two):,} 条 / {two_slots:,} 码位",
              f"- 四字简词：{len(four):,} 条 / {four_slots:,} 码位",
              f"- 两类重叠：{overlap:,} 码位",
              f"- 合并后：{len(rows):,} 个四码位",
              f"- 仅二字词：{sum(r['has_two'] and not r['has_four'] for r in rows):,}",
              f"- 仅四字词：{sum(r['has_four'] and not r['has_two'] for r in rows):,}", "",
              "本表尚未附加退火权重；二字词与四字简词的原始证据分开保留。"]
    (LEX / "目标词库_合并报告.md").write_text("\n".join(report)+"\n", encoding="utf-8")
    print("\n".join(report))

if __name__ == "__main__": main()
