# -*- coding: utf-8 -*-
"""按实际发布候选顺序生成夜莺 v0.7 字词撞车与裁决 CSV。"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import yaml

BROOT = Path(__file__).resolve().parents[1]
BASE = BROOT.parent


def read_table(path: Path) -> dict[str, list[str]]:
    result = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        phrase, code = line.split("\t")
        result[code].append(phrase)
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", type=Path, default=BASE / "releases/v0.7")
    ap.add_argument("--elements", type=Path,
                    default=BROOT / "work/v07_release_final_build/elements.yaml")
    ap.add_argument("--output", type=Path,
                    default=BROOT / "work/v07_unlocked_audit/夜莺码v0.7字词撞车与裁决.csv")
    args = ap.parse_args()

    no_yield = read_table(args.release / "夜莺码v0.7纯单版_不让位.txt")
    mixed = read_table(args.release / "夜莺码v0.7字词版_无简词.txt")
    elements = yaml.safe_load(args.elements.read_text(encoding="utf-8"))
    char_rank = {}
    for item in elements:
        char = str(item["词"])
        rank = int(item.get("排序序号", 10**12)) + 1
        char_rank[char] = min(rank, char_rank.get(char, rank))

    words_by_code = defaultdict(list)
    with (BROOT / "work/lexicon/二字词_精选60000.tsv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        for rank, row in enumerate(csv.DictReader(handle, delimiter="\t"), 1):
            words_by_code[str(row["code"])].append((rank, str(row["word"])))

    target_slots = {}
    with (BROOT / "work/lexicon/目标词库_四码位.tsv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            target_slots[str(row["code"])] = row

    decisions_data = yaml.safe_load((BROOT / "work/字词冲突裁决.yaml").read_text(
        encoding="utf-8")) or {}
    decisions = decisions_data.get("decisions") or {}
    rows = []
    for code, phrases in no_yield.items():
        if len(code) != 4 or code not in words_by_code:
            continue
        word_rows = words_by_code[code]
        words = [word for _, word in word_rows]
        for char_position, char in enumerate(phrases, 1):
            if len(char) != 1 or char not in char_rank:
                continue
            actual = mixed.get(code, [])
            actual_position = actual.index(char) + 1 if char in actual else ""
            first = actual[0] if actual else ""
            decision = decisions.get(code) or {}
            if str(decision.get("char", "")) == char:
                action = str(decision.get("action", ""))
                note = str(decision.get("note", ""))
                status = "已裁决"
            else:
                note = ""
                status = "按发布候选顺序落实"
                action = "word_first" if first in words else "retain_single"
            rows.append({
                "单字": char,
                "字频序": char_rank[char],
                "相撞码": code,
                "不让位表候选": char_position,
                "综合表候选": actual_position,
                "综合表首选": first,
                "二字词最高序": word_rows[0][0],
                "二字词": " ".join(words),
                "四字简词最高序": str(target_slots.get(code, {}).get("four_top_rank", "")),
                "四字简词": str(target_slots.get(code, {}).get("four_words", "")).replace("|", " "),
                "处理动作": action,
                "状态": status,
                "裁决备注": note,
            })

    # 无简词发布表不会出现只撞四字简词的历史裁决，但汇总 CSV 仍保留这些证据。
    present = {(str(row["相撞码"]), str(row["单字"])) for row in rows}
    for code, decision in decisions.items():
        char = str(decision.get("char", ""))
        if (str(code), char) in present:
            continue
        slot = target_slots.get(str(code), {})
        if not slot:
            continue
        rows.append({
            "单字": char,
            "字频序": char_rank.get(char, ""),
            "相撞码": str(code),
            "不让位表候选": "",
            "综合表候选": "",
            "综合表首选": "",
            "二字词最高序": str(slot.get("two_top_rank", "")),
            "二字词": str(slot.get("two_words", "")).replace("|", " "),
            "四字简词最高序": str(slot.get("four_top_rank", "")),
            "四字简词": str(slot.get("four_words", "")).replace("|", " "),
            "处理动作": str(decision.get("action", "")),
            "状态": "历史裁决（无简词版未收录）",
            "裁决备注": str(decision.get("note", "")),
        })
    rows.sort(key=lambda row: (int(row["字频序"]), str(row["相撞码"]), str(row["单字"])))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"collisions={len(rows)} output={args.output}")


if __name__ == "__main__":
    main()
