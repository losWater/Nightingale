# -*- coding: utf-8 -*-
"""构造终局字词分离实验：1500字×前20000词、3500字×前5000词硬保护。"""
from __future__ import annotations

import csv
import argparse
import datetime as dt
import json
from pathlib import Path
from copy import deepcopy

import yaml

BASE = Path(__file__).resolve().parents[1]
WORK = BASE / "work"
LEX = WORK / "lexicon"
SPLIT = WORK / "slot_splits"
# 固定笔画或既定结构造成、无法通过排键移动的词位；不伪装成优化器可解目标。
FIXED = {"wjhv", "iruu", "yuhh"}


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def weight(rank):
    if rank <= 5000: return 1.0
    if rank <= 20000: return 0.5
    if rank <= 30000: return 0.2
    return 0.05


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top1500-words", type=int, default=20000)
    ap.add_argument("--top3500-words", type=int, default=5000)
    ap.add_argument("--novel-slots", type=int, default=5000)
    args = ap.parse_args()
    slots = rows(LEX / "二字词_四码位.tsv")
    merged = {r["code"]: r for r in rows(LEX / "目标词库_四码位.tsv")}
    old = rows(SPLIT / "词位训练集.tsv")

    mandatory = {r["code"] for r in slots if r["top_rank"] and int(r["top_rank"]) <= args.top1500_words}
    novel = [r["code"] for r in old if r["reason"] == "two_novel_explore" and r["code"] not in mandatory]
    if len(novel) < 5000:
        used = mandatory | set(novel)
        tail = [r for r in slots if r["code"] not in used and int(r["top_rank"] or 999999) > args.top1500_words]
        novel += [r["code"] for r in tail[:args.novel_slots-len(novel)]]
    novel = novel[:args.novel_slots]
    four = {r["code"] for r in old if r["has_four"] == "1"}
    selected_two = mandatory | set(novel)

    targets = {}
    for code in selected_two | four:
        r = merged[code]
        two = int(r["two_top_rank"]) if code in selected_two and r["two_top_rank"] else None
        four_rank = int(r["four_top_rank"]) if code in four and r["four_top_rank"] else None
        soft = (weight(two) if two else 0.0) + (weight(four_rank) * 0.25 if four_rank else 0.0)
        hard_top = (0 if not two or code in FIXED else
                    3500 if two <= args.top3500_words else
                    1500 if two <= args.top1500_words else 0)
        targets[code] = {"soft": soft, "hard": bool(hard_top), "hard_character_top": hard_top}

    cfg = deepcopy(yaml.safe_load((WORK / "analysis_config_compat.yaml").read_text(encoding="utf-8")))
    cfg["optimization"]["objective"]["character_word_collision"]["targets"] = targets
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = WORK / "final_protection_runs" / (
        f"hard_1500x{args.top1500_words}_3500x{args.top3500_words}_novel{args.novel_slots}_{stamp}")
    out.mkdir(parents=True)
    (out / "input_config.yaml").write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
    manifest = {"mandatory_two_slots": len(mandatory), "novel_two_slots": len(novel),
                "four_slots": len(four), "total_targets": len(targets),
                "hard_rule": {"top1500_words": args.top1500_words,
                              "top3500_words": args.top3500_words},
                "unreasonable_codes": False, "structural_exceptions": sorted(FIXED)}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OUT={out}")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
