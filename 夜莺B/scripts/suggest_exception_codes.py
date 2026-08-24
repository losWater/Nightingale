# -*- coding: utf-8 -*-
"""为少量单字寻找只改变一个形码的无冲突容错全码。"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parents[1]
KEYS = "abcdefghijklmnopqrstuvwxyz"
TARGETS = "肿仕蔬怖柚"
# 大致按常用键位舒适度排序；真正定案仍由记忆逻辑优先。
COMFORT = "fjdksla;ghrueiwotynmvcxbzqp".replace(";", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", type=Path)
    ap.add_argument("code", type=Path)
    ap.add_argument("--move", action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    elements = yaml.safe_load((BASE / "work" / "analysis_elements.yaml").read_text(encoding="utf-8"))
    roots = set(yaml.safe_load((BASE / "work" / "根集.yaml").read_text(encoding="utf-8"))["roots"])
    mapping = yaml.safe_load(args.config.read_text(encoding="utf-8"))["form"]["mapping"]
    raw_codes = [x.split("\t")[1] for x in args.code.read_text(encoding="utf-8").splitlines()]
    moves = dict(spec.split("=", 1) for spec in args.move)

    def trace(element):
        current = str(element)
        seen = set()
        while current not in seen:
            seen.add(current)
            value = mapping.get(current)
            if isinstance(value, str):
                return current
            if isinstance(value, dict) and "element" in value:
                current = str(value["element"])
                continue
            return None
        return None

    codes = []
    owners = []
    for item, raw in zip(elements, raw_codes):
        chars = list(raw)
        pair = []
        for pos, slot in zip((2, 3), item["元素序列"][2:4]):
            owner = trace(slot["element"])
            pair.append(owner if owner in roots else None)
            if owner in moves:
                chars[pos] = moves[owner]
        codes.append("".join(chars))
        owners.append(pair)

    char_counts = Counter(codes)
    word_slots = {}
    with (BASE / "work" / "lexicon" / "目标词库_四码位.tsv").open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            word_slots[row["code"]] = row

    order = sorted(range(len(elements)), key=lambda i: -int(elements[i].get("频率", 0)))
    char_rank = {i: rank for rank, i in enumerate(order, 1)}
    comfort_rank = {key: rank for rank, key in enumerate(COMFORT)}
    rows = []
    for character in TARGETS:
        matches = [i for i, item in enumerate(elements) if item["词"] == character]
        if not matches:
            continue
        i = min(matches, key=lambda x: char_rank[x])
        original = codes[i]
        for changed_pos, preservation in ((3, "保留首根"), (2, "保留末根")):
            for key in KEYS:
                if key == original[changed_pos]:
                    continue
                candidate = original[:changed_pos] + key + original[changed_pos + 1:]
                lex = word_slots.get(candidate)
                rows.append({
                    "单字": character,
                    "字频序": char_rank[i],
                    "原码": original,
                    "候选码": candidate,
                    "策略": preservation,
                    "保留根": owners[i][0 if changed_pos == 3 else 1] or "笔画/非根",
                    "改入键": key,
                    "单字撞数": char_counts[candidate],
                    "二字词撞": lex["two_words"] if lex and lex["two_words"] else "",
                    "四字词撞": lex["four_words"] if lex and lex["four_words"] else "",
                    "舒适序": comfort_rank[key],
                })

    rows.sort(key=lambda r: (
        r["单字"], r["单字撞数"] > 0, bool(r["二字词撞"]), bool(r["四字词撞"]),
        r["策略"] != "保留首根", r["舒适序"], r["候选码"],
    ))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader(); writer.writerows(rows)
    for character in TARGETS:
        clean = [r for r in rows if r["单字"] == character and not r["单字撞数"]
                 and not r["二字词撞"] and not r["四字词撞"]]
        print(character, clean[:10])


if __name__ == "__main__":
    main()
