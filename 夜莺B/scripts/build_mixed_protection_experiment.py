# -*- coding: utf-8 -*-
"""构造 1674 黑洞核心 + 3527 质数常用层的退火实验。"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from copy import deepcopy
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
WORK = BASE / "work"
LEX = WORK / "lexicon"
SPLIT = WORK / "slot_splits"
ASSET = WORK / "混合高频保护资产"
CORE = ASSET / "内部前1500_并_外部前1400_1674字.txt"
COMMON = ASSET / "内部前3300_并_外部前3000_3527字.txt"
FIXED = {"wjhv", "iruu", "yuhh"}


def tsv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def chars(path: Path):
    return {x.strip() for x in path.read_text(encoding="utf-8-sig").splitlines() if x.strip()}


def weight(rank):
    if rank <= 5000: return 1.0
    if rank <= 20000: return 0.5
    if rank <= 30000: return 0.2
    return 0.05


def auxiliary_records(rows, mapping):
    """生成与显式优化排序后的内部字符索引对齐的二字词辅助码资产。"""
    char_sound = {}
    for original, row in enumerate(rows):
        sequence = row.get("元素序列", [])
        if len(sequence) < 2:
            continue
        first = mapping.get(sequence[0].get("element"))
        second = mapping.get(sequence[1].get("element"))
        if isinstance(first, str) and isinstance(second, str) and len(first) == len(second) == 1:
            char_sound.setdefault((str(row["词"]), first + second), original)

    lexicon = tsv(LEX / "二字词_精选60000.tsv")
    by_code = {}
    for row in lexicon:
        by_code.setdefault(row["code"], []).append(row)
    records = []
    group = 0
    missing = []
    for code, items in by_code.items():
        if len(items) <= 1:
            continue
        # 原词表已经按频次证据降序，同组内保持该顺序。
        emitted = []
        for row in items:
            word = row["word"]
            first = char_sound.get((word[0], code[:2]))
            second = char_sound.get((word[1], code[2:]))
            if first is None or second is None:
                missing.append((word, code))
                continue
            emitted.append({"first_index": first, "second_index": second,
                            "group": group, "weight": float(row["score"])})
        if len(emitted) > 1:
            records.extend(emitted)
            group += 1
    if missing:
        raise AssertionError(f"辅助码资产缺少 {len(missing)} 个字音索引，示例：{missing[:5]}")
    return records, group


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--core-words", type=int, default=15000)
    ap.add_argument("--common-words", type=int, default=5000)
    ap.add_argument("--novel-slots", type=int, default=5000)
    args = ap.parse_args()

    core, common = chars(CORE), chars(COMMON)
    if not core <= common:
        raise SystemExit("1674核心层不是3527常用层的子集")
    elements = yaml.safe_load((WORK / "analysis_elements.yaml").read_text(encoding="utf-8"))
    core_rows = [x for x in elements if str(x["词"]) in core]
    common_rows = [x for x in elements if str(x["词"]) in common - core]
    rest_rows = [x for x in elements if str(x["词"]) not in common]
    # 保护层内的冷门读音也必须参与重码约束，防止多音字用零频读音偷位置。
    # 只提升到最小正频率1，不让它扭曲加权键长和手感指标。
    for row in core_rows + common_rows:
        if int(row.get("频率", 0)) <= 0:
            row["频率"] = 1
    reordered = core_rows + common_rows + rest_rows
    for order, row in enumerate(reordered):
        row["排序序号"] = order
    core_top, common_top = len(core_rows), len(core_rows) + len(common_rows)

    slots = tsv(LEX / "二字词_四码位.tsv")
    merged = {r["code"]: r for r in tsv(LEX / "目标词库_四码位.tsv")}
    old = tsv(SPLIT / "词位训练集.tsv")
    mandatory = {r["code"] for r in slots if r["top_rank"] and int(r["top_rank"]) <= args.core_words}
    novel = [r["code"] for r in old if r["reason"] == "two_novel_explore" and r["code"] not in mandatory]
    if len(novel) < args.novel_slots:
        used = mandatory | set(novel)
        tail = [r for r in slots if r["code"] not in used and int(r["top_rank"] or 999999) > args.core_words]
        novel += [r["code"] for r in tail[:args.novel_slots - len(novel)]]
    novel = novel[:args.novel_slots]
    four = {r["code"] for r in old if r["has_four"] == "1"}
    selected_two = mandatory | set(novel)

    targets = {}
    for code in selected_two | four:
        row = merged[code]
        two = int(row["two_top_rank"]) if code in selected_two and row["two_top_rank"] else None
        four_rank = int(row["four_top_rank"]) if code in four and row["four_top_rank"] else None
        soft = (weight(two) if two else 0.0) + (weight(four_rank) * 0.25 if four_rank else 0.0)
        hard_top = (0 if not two or code in FIXED else
                    common_top if two <= args.common_words else
                    core_top if two <= args.core_words else 0)
        targets[code] = {"soft": soft, "hard": bool(hard_top), "hard_character_top": hard_top}

    cfg = deepcopy(yaml.safe_load((WORK / "analysis_config_compat.yaml").read_text(encoding="utf-8")))
    objective = cfg["optimization"]["objective"]
    objective["characters_full"]["tiers"][0]["top"] = core_top
    objective["characters_full"]["tiers"][1]["top"] = common_top
    objective["characters_short"]["tiers"][0]["top"] = core_top
    objective["characters_short"]["tiers"][1]["top"] = common_top
    cross = objective["character_word_collision"]
    cross["hard_character_top"] = core_top
    cross["character_tiers"][0]["top"] = core_top
    cross["character_tiers"][1]["top"] = common_top
    cross["targets"] = targets
    aux_records, aux_groups = auxiliary_records(reordered, cfg["form"]["mapping"])
    objective["auxiliary_two_char"] = {"weight": 1.0, "records": aux_records}

    # 条件安排：月的候选键只有在日不位于同键时才合法。
    for arrangement in cfg["form"]["mapping_space"]["月"]:
        arrangement["condition"] = [{"element": "日", "op": "不是", "value": arrangement["value"]}]

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = WORK / "mixed_protection_runs" / f"blackhole1674_prime3527_{stamp}"
    out.mkdir(parents=True)
    config_path = out / "input_config.yaml"
    elements_path = out / "analysis_elements_1674_3527.yaml"
    config_path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
    elements_path.write_text(yaml.safe_dump(reordered, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
    manifest = {
        "core": {"name": "1674黑洞核心", "characters": len(core), "reading_assets": core_top},
        "common": {"name": "3527质数常用", "characters": len(common), "reading_assets": common_top},
        "hard_rule": {"core_words": args.core_words, "common_words": args.common_words},
        "constraint": "日 != 月", "mandatory_two_slots": len(mandatory),
        "novel_two_slots": len(novel), "four_slots": len(four), "total_targets": len(targets),
        "auxiliary_two_char": {"records": len(aux_records), "groups": aux_groups, "weight": 1.0},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OUT={out}")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
