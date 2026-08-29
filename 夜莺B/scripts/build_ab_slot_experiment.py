# -*- coding: utf-8 -*-
"""构造“纯高频词位 A / 高频核心+尾部新词位 B”的无泄漏 A/B 退火输入。"""
from __future__ import annotations

import csv
import datetime as dt
import json
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parents[1]
WORK = BASE / "work"
LEX = WORK / "lexicon"
SPLIT = WORK / "slot_splits"
FIXED = {"wjhv", "iruu"}


def read_tsv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def word_weight(rank):
    if rank <= 2000: return 1.0
    if rank <= 10000: return 0.5
    if rank <= 30000: return 0.2
    return 0.05


def target(row, allow_two, allow_four):
    two = int(row["two_top_rank"]) if allow_two and row["two_top_rank"] else None
    four = int(row["four_top_rank"]) if allow_four and row["four_top_rank"] else None
    soft = (word_weight(two) if two else 0.0) + (word_weight(four) * 0.25 if four else 0.0)
    hard_top = 0 if not two or row["code"] in FIXED else 3500 if two <= 2000 else 1500 if two <= 10000 else 0
    return {"soft": soft, "hard": bool(hard_top), "hard_character_top": hard_top}


def write_rows(path, rows, label):
    fields = ["experiment", "code", "two_slot_rank", "two_top_rank", "two_words", "selection"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=fields, delimiter="\t"); wr.writeheader()
        for rank, row, selection in rows:
            wr.writerow({"experiment": label, "code": row["code"], "two_slot_rank": rank,
                         "two_top_rank": row["top_rank"], "two_words": row["words"],
                         "selection": selection})


def main():
    slots = read_tsv(LEX / "二字词_四码位.tsv")
    merged = {row["code"]: row for row in read_tsv(LEX / "目标词库_四码位.tsv")}
    slot_rank = {row["code"]: i for i, row in enumerate(slots, 1)}
    by_code = {row["code"]: row for row in slots}

    # A：聚合权重最高的 15,000 个二字词位。
    a_codes = [row["code"] for row in slots[:15000]]

    # B：相同排名口径的前 10,000 核心 + 旧切分中刻意从三个尾段抽出的 5,000 新词位。
    core = [row["code"] for row in slots[:10000]]
    old_train = read_tsv(SPLIT / "词位训练集.tsv")
    explore = [row["code"] for row in old_train if row["reason"] == "two_novel_explore"
               and row["code"] not in set(core)]
    # 极少数探索位若因聚合权重进入前 10k，用原训练集中更靠后的未选二字位补齐。
    if len(explore) < 5000:
        candidates = [row for row in old_train if row["has_two"] == "1"
                      and row["code"] not in set(core) | set(explore)]
        candidates.sort(key=lambda row: (int(row["two_rank"] or 999999), row["code"]))
        explore += [row["code"] for row in candidates[:5000-len(explore)]]
    if len(explore) != 5000:
        raise ValueError(f"B 探索位不是 5000：{len(explore)}")
    b_codes = core + explore
    if len(set(a_codes)) != 15000 or len(set(b_codes)) != 15000:
        raise AssertionError("A/B 二字训练位必须各为 15000 个不同码位")

    # 四字压力双方固定不变，沿用已经选定的训练集四字码位。
    four_codes = {row["code"] for row in old_train if row["has_four"] == "1"}
    train_union = set(a_codes) | set(b_codes) | four_codes

    # 从双方训练并集之外取公共隐藏集：按原二字槽权重优先，固定 5,000 位。
    validation_codes = [row["code"] for row in slots if row["code"] not in train_union][:5000]
    if len(validation_codes) != 5000:
        raise ValueError("公共隐藏验证位不足")

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = WORK / "ab_slot_runs" / f"frequency_vs_novel_{stamp}"
    out.mkdir(parents=True)
    base = yaml.safe_load((WORK / "analysis_config_compat.yaml").read_text(encoding="utf-8"))

    variants = {"A_frequency15000": a_codes, "B_core10000_novel5000": b_codes}
    for name, codes in variants.items():
        run = out / name; run.mkdir()
        config = deepcopy(base)
        selected_two = set(codes)
        all_codes = selected_two | four_codes
        targets = {}
        for code in all_codes:
            row = merged[code]
            targets[code] = target(row, code in selected_two, code in four_codes)
        config["optimization"]["objective"]["character_word_collision"]["targets"] = targets
        (run / "input_config.yaml").write_text(
            yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
        selected = [(slot_rank[code], by_code[code], "frequency_core" if code in set(core) else
                     "frequency_tail" if name.startswith("A_") else "novel_tail") for code in codes]
        write_rows(run / "二字训练位.tsv", selected, name)

    validation = [(slot_rank[code], by_code[code], "common_hidden") for code in validation_codes]
    write_rows(out / "公共隐藏验证位.tsv", validation, "common_validation")
    manifest = {
        "created": stamp, "A_two_slots": 15000, "B_two_slots": 15000,
        "B_core": 10000, "B_novel": 5000, "fixed_four_slots": len(four_codes),
        "common_validation_slots": len(validation_codes),
        "A_B_two_overlap": len(set(a_codes) & set(b_codes)),
        "A_only": len(set(a_codes) - set(b_codes)), "B_only": len(set(b_codes) - set(a_codes)),
        "leakage": len(set(validation_codes) & train_union),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "实验说明.md").write_text(
        "# 词位训练 A/B\n\n"
        "- A：聚合权重最高的 15,000 个二字词位。\n"
        "- B：聚合权重最高的 10,000 个核心位，加 5,000 个分频段探索的新词位。\n"
        f"- 双方固定使用同一批 {len(four_codes):,} 个四字训练位。\n"
        "- 公共隐藏验证位完全位于双方训练并集之外，零码位泄漏。\n"
        "- 不使用任何无理码。\n", encoding="utf-8")
    print(f"OUT={out}")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
