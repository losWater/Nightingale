# -*- coding: utf-8 -*-
"""列出指定夜莺布局中，单字全码与目标词库四码位的碰撞明细。"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parents[1]
FIXED_BASELINE = {"wjhv", "iruu"}


def word_weight(rank: int) -> float:
    if rank <= 2000:
        return 1.0
    if rank <= 10000:
        return 0.5
    if rank <= 30000:
        return 0.2
    return 0.05


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path, help="布局 config.yaml")
    parser.add_argument("code", type=Path, help="与 analysis_elements.yaml 对齐的 code.txt")
    parser.add_argument("--elements", type=Path, default=BASE / "work" / "analysis_elements.yaml")
    parser.add_argument("--move", action="append", default=[], help="附加移动，如 夕=m；可重复")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--ignore-root",
        action="append",
        default=[],
        help="ignore roots added after a frozen experiment asset was built",
    )
    args = parser.parse_args()

    elements = yaml.safe_load(args.elements.read_text(encoding="utf-8"))
    roots = set(yaml.safe_load((BASE / "work" / "根集.yaml").read_text(encoding="utf-8"))["roots"])
    roots.difference_update(args.ignore_root)
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    mapping = config["form"]["mapping"]
    code_rows = [line.split("\t") for line in args.code.read_text(encoding="utf-8").splitlines()]
    if len(code_rows) != len(elements):
        raise ValueError(f"code/elements 行数不一致: {len(code_rows)} != {len(elements)}")
    for item, row in zip(elements, code_rows):
        if str(item["词"]) != row[0]:
            raise ValueError(f"code/elements 错位: {item['词']} != {row[0]}")

    moves = {}
    for text in args.move:
        root, key = text.split("=", 1)
        moves[root] = key.lower()

    def trace(element: str):
        current = str(element)
        seen = set()
        while current not in seen:
            seen.add(current)
            value = mapping.get(current)
            if isinstance(value, str):
                return current, value
            if isinstance(value, dict) and "element" in value:
                current = str(value["element"])
                continue
            return None, None
        return None, None

    full_codes = []
    for item, code_row in zip(elements, code_rows):
        code = list(code_row[1])
        for pos, slot in zip((2, 3), item["元素序列"][2:4]):
            owner, _ = trace(slot["element"])
            if owner in roots and owner in moves:
                code[pos] = moves[owner]
        full_codes.append("".join(code))


    targets = {}
    lexicon_path = BASE / "work" / "lexicon" / "目标词库_四码位.tsv"
    with lexicon_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            two_rank = int(row["two_top_rank"]) if row["two_top_rank"] else None
            four_rank = int(row["four_top_rank"]) if row["four_top_rank"] else None
            targets[row["code"]] = (row, two_rank, four_rank)

    # 与 libchai 的预处理顺序一致：新版资产可显式指定保护顺序；旧资产回退到频率序。
    if any(item.get("排序序号") is not None for item in elements):
        order = sorted(range(len(elements)), key=lambda i: (
            int(elements[i].get("排序序号", 10**12)), i
        ))
    else:
        order = sorted(range(len(elements)), key=lambda i: -int(elements[i].get("频率", 0)))

    objective = config["optimization"]["objective"]["character_word_collision"]
    configured_targets = objective["targets"]
    tiers = objective.get("character_tiers", [])

    def character_factor(rank: int) -> float:
        for tier in tiers:
            if rank <= int(tier["top"]):
                return float(tier["factor"])
        return 0.0
    result = []
    for char_rank, i in enumerate(order[:5000], 1):
        # A character that is actually emitted in fewer than four keys never
        # competes with a four-key word at its theoretical full-code slot.
        if len(code_rows[i][3]) < len(code_rows[i][1]):
            continue
        code = full_codes[i]
        if code not in targets or code not in configured_targets:
            continue
        lex, two_rank, four_rank = targets[code]
        target = configured_targets[code]
        char_factor = character_factor(char_rank)
        total_score = char_factor * float(target.get("soft", 0.0))
        # 下面两项只为展示二字／四字来源；总分严格以本轮配置中的 target.soft 为准。
        two_score = char_factor * word_weight(two_rank) if two_rank else 0.0
        four_score = max(0.0, total_score - two_score)
        hard_top = int(target.get("hard_character_top", 0))
        is_hard = bool(target.get("hard", False) and char_rank <= hard_top)
        result.append({
            "类型": "固定基线" if code in FIXED_BASELINE else "硬词撞" if is_hard else "软词撞",
            "加权分": total_score,
            "单字": elements[i]["词"],
            "字频序": char_rank,
            "全码": code,
            "二字词最高序": two_rank or "",
            "二字词": lex["two_words"],
            "二字贡献": two_score,
            "四字词最高序": four_rank or "",
            "四字词": lex["four_words"],
            "四字贡献": four_score,
        })

    result.sort(key=lambda row: (-row["加权分"], row["字频序"], row["全码"]))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(result[0]) if result else []
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(result)

    soft = [row for row in result if row["类型"] == "软词撞"]
    print(f"总明细 {len(result)} 条；软词撞 {len(soft)} 条；软词撞加权分 {sum(x['加权分'] for x in soft):.6f}")
    print(args.output)


if __name__ == "__main__":
    main()
