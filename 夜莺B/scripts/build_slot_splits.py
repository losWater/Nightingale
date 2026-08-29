# -*- coding: utf-8 -*-
"""按四码词位而非词条构造训练／验证／最终测试集，严格防止码位泄漏。"""
from __future__ import annotations

import argparse
import csv
import hashlib
import math
from collections import defaultdict
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
LEX = BASE / "work" / "lexicon"


def read_tsv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def stable_key(seed, text):
    return hashlib.sha256(f"{seed}:{text}".encode()).hexdigest()


def allocate(groups, total):
    """按各前缀候选数平方根分配整数配额。"""
    weights = {key: math.sqrt(len(values)) for key, values in groups.items() if values}
    weight_sum = sum(weights.values())
    raw = {key: total * weight / weight_sum for key, weight in weights.items()}
    quota = {key: min(len(groups[key]), int(value)) for key, value in raw.items()}
    remaining = total - sum(quota.values())
    order = sorted(weights, key=lambda k: (-(raw[k] - int(raw[k])), k))
    while remaining:
        changed = False
        for key in order:
            if quota[key] < len(groups[key]):
                quota[key] += 1; remaining -= 1; changed = True
                if not remaining: break
        if not changed:
            raise ValueError(f"候选不足，无法分配 {total}")
    return quota


def paired_stratified(candidates, each, seed):
    """一次抽取两份等规模集合，再交错分给探索与验证，保持分布一致。"""
    groups = defaultdict(list)
    for row in candidates:
        groups[row["prefix"]].append(row)
    for prefix, values in groups.items():
        # 先保留该频段中排名靠前、来源更可靠的词位，避免尾部专名／机器短语
        # 因随机采样进入训练；再对入选池稳定洗牌，使探索与验证质量相当。
        values.sort(key=lambda x: (
            int(x["two_rank"]) if x["two_rank"] != "" else int(x["four_rank"]),
            -int(x["two_groups"] or x["four_sources"] or 0),
            x["code"],
        ))
    quota = allocate(groups, each * 2)
    explore, validation = [], []
    for prefix, count in quota.items():
        chosen = groups[prefix][:count]
        chosen.sort(key=lambda x: stable_key(seed, x["code"]))
        for index, row in enumerate(chosen):
            (explore if index % 2 == 0 else validation).append(row)
    # 奇数配额可能让总量差一两个；从较大集合移到较小集合，仍保持码位不重合。
    while len(explore) > each:
        validation.append(explore.pop())
    while len(validation) > each:
        explore.append(validation.pop())
    if len(explore) != each or len(validation) != each:
        raise AssertionError((len(explore), len(validation), each))
    return explore, validation


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260825)
    ap.add_argument("--output", type=Path, default=BASE / "work" / "slot_splits")
    args = ap.parse_args()

    two_rows = read_tsv(LEX / "二字词_精选60000.tsv")
    four_rows = read_tsv(LEX / "四字简词_精选.tsv")
    by_code = {}
    two_words, four_words = defaultdict(list), defaultdict(list)
    for rank, row in enumerate(two_rows, 1):
        two_words[row["code"]].append(row["word"])
        if row["code"] not in by_code:
            by_code[row["code"]] = {
                "code": row["code"], "prefix": row["code"][:2], "two_rank": rank,
                "four_rank": "", "two_word": row["word"], "four_word": "",
                "two_groups": row["groups"], "four_sources": "",
            }
    for rank, row in enumerate(four_rows, 1):
        four_words[row["code"]].append(row["word"])
        item = by_code.setdefault(row["code"], {
            "code": row["code"], "prefix": row["code"][:2], "two_rank": "",
            "four_rank": rank, "two_word": "", "four_word": row["word"],
            "two_groups": "", "four_sources": row["corpus_source_count"],
        })
        if item["four_rank"] == "":
            item["four_rank"] = rank; item["four_word"] = row["word"]
            item["four_sources"] = row["corpus_source_count"]

    all_two_codes = set(two_words)
    all_four_codes = set(four_words)
    assignments, reasons, bands = {}, {}, {}

    # 所有前一万二字高频位与前两千四字简词位，统一归入训练核心。
    for code, row in by_code.items():
        if row["two_rank"] != "" and int(row["two_rank"]) <= 10000:
            assignments[code] = "train"; reasons[code] = "two_core"; bands[code] = "two_1_10000"
        if row["four_rank"] != "" and int(row["four_rank"]) <= 2000:
            assignments[code] = "train"
            reasons[code] = reasons.get(code, "") + ("+" if code in reasons else "") + "four_core"
            bands[code] = bands.get(code, "") + ("+" if code in bands else "") + "four_1_2000"

    two_band_specs = [(10001, 20000, 2000), (20001, 30000, 1500), (30001, 60000, 1500)]
    for low, high, each in two_band_specs:
        candidates = []
        for code, row in by_code.items():
            rank = row["two_rank"]
            if code in assignments or rank == "" or not (low <= int(rank) <= high):
                continue
            candidates.append(row)
        explore, validation = paired_stratified(candidates, each, args.seed + low)
        for split, selected in (("train", explore), ("validation", validation)):
            for row in selected:
                code = row["code"]; assignments[code] = split
                reasons[code] = "two_novel_explore" if split == "train" else "two_hidden"
                bands[code] = f"two_{low}_{high}"

    # 四字探索只从二字词完全未覆盖的独占码位中抽取。
    four_band_specs = [(2001, 5000, 1000), (5001, 10000, 800), (10001, len(four_rows), 700)]
    for low, high, each in four_band_specs:
        candidates = []
        for code, row in by_code.items():
            rank = row["four_rank"]
            if code in assignments or code in all_two_codes or rank == "" or not (low <= int(rank) <= high):
                continue
            candidates.append(row)
        explore, validation = paired_stratified(candidates, each, args.seed + 100000 + low)
        for split, selected in (("train", explore), ("validation", validation)):
            for row in selected:
                code = row["code"]; assignments[code] = split
                reasons[code] = "four_only_explore" if split == "train" else "four_only_hidden"
                bands[code] = f"four_{low}_{high}"

    for code in by_code:
        if code not in assignments:
            assignments[code] = "test"; reasons[code] = "untouched_final"; bands[code] = "reserve"

    output_rows = []
    for code, row in by_code.items():
        output_rows.append({
            "split": assignments[code], "reason": reasons[code], "band": bands[code],
            **row, "has_two": int(code in all_two_codes), "has_four": int(code in all_four_codes),
            "two_words": " ".join(two_words[code]), "four_words": " ".join(four_words[code]),
        })
    output_rows.sort(key=lambda x: ({"train": 0, "validation": 1, "test": 2}[x["split"]], x["code"]))
    args.output.mkdir(parents=True, exist_ok=True)
    fields = list(output_rows[0])
    names = {"train": "词位训练集.tsv", "validation": "词位验证集.tsv", "test": "词位最终测试集.tsv"}
    for split, name in names.items():
        rows = [x for x in output_rows if x["split"] == split]
        with (args.output / name).open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
            writer.writeheader(); writer.writerows(rows)

    sets = {split: {x["code"] for x in output_rows if x["split"] == split} for split in names}
    assert not (sets["train"] & sets["validation"] or sets["train"] & sets["test"]
                or sets["validation"] & sets["test"])
    report = ["# 词位训练／验证／最终测试切分", "", f"- 固定随机种子：{args.seed}",
              "- 切分单位：四码位；同码二字词和四字简词永远属于同一集合。", ""]
    for split, title in (("train", "训练"), ("validation", "隐藏验证"), ("test", "最终测试")):
        rows = [x for x in output_rows if x["split"] == split]
        report.append(f"- {title}：{len(rows)} 码位（二字 {sum(x['has_two'] for x in rows)}；四字 {sum(x['has_four'] for x in rows)}）")
    report += ["", "训练集中的尾部探索码位只适合软压力；隐藏验证与最终测试不得进入退火目标。", ""]
    (args.output / "切分报告.md").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
