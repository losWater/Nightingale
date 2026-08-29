# -*- coding: utf-8 -*-
"""在固定布局附近枚举单根移动，优先消除扩展字词碰撞。"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parents[1]
KEYS = "abcdefghijklmnopqrstuvwxyz"
FIXED = {"wjhv", "iruu", "yuhh"}


def duplicates(codes, order, top):
    counts = Counter(codes[i] for i in order[:top])
    return sum(n - 1 for n in counts.values() if n > 1)


def short_codes(full, order):
    first = {}
    for i in order:
        first.setdefault(full[i][:3], i)
    return [code[:3] if first[code[:3]] == i else code for i, code in enumerate(full)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", type=Path)
    ap.add_argument("code", type=Path)
    ap.add_argument("--move", action="append", default=[])
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--inspect-only", action="store_true")
    ap.add_argument("--swaps", action="store_true", help="枚举碰撞相关根与所有主根的键位互换")
    ap.add_argument("--root", help="只枚举指定主根的移动")
    ap.add_argument("--top1500-words", type=int, default=10000)
    ap.add_argument("--top3500-words", type=int, default=2000)
    args = ap.parse_args()

    elements = yaml.safe_load((BASE / "work" / "analysis_elements.yaml").read_text(encoding="utf-8"))
    root_cfg = yaml.safe_load((BASE / "work" / "根集.yaml").read_text(encoding="utf-8"))
    roots = list(root_cfg["roots"])
    mapping = yaml.safe_load(args.config.read_text(encoding="utf-8"))["form"]["mapping"]
    raw_codes = [x.split("\t")[1] for x in args.code.read_text(encoding="utf-8").splitlines()]
    order = sorted(range(len(elements)), key=lambda i: -int(elements[i].get("频率", 0)))

    initial_moves = {}
    for spec in args.move:
        root, key = spec.split("=", 1)
        initial_moves[root] = key.lower()

    word_ranks = {}
    with (BASE / "work" / "lexicon" / "目标词库_四码位.tsv").open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            word_ranks[row["code"]] = int(row["two_top_rank"]) if row["two_top_rank"] else None

    def trace(element):
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

    owners = []
    root_keys = {}
    for root in roots:
        _, key = trace(root)
        if root in initial_moves:
            key = initial_moves[root]
        if isinstance(key, str) and key in KEYS:
            root_keys[root] = key
    for item in elements:
        pair = []
        for slot in item["元素序列"][2:4]:
            owner, _ = trace(slot["element"])
            pair.append(owner if owner in roots else None)
        owners.append(pair)

    def make_codes(extra_root=None, destination=None, extra_moves=None):
        extra_moves = extra_moves or {}
        result = []
        for raw, pair in zip(raw_codes, owners):
            chars = list(raw)
            for pos, owner in zip((2, 3), pair):
                if owner in initial_moves:
                    chars[pos] = initial_moves[owner]
                if owner in extra_moves:
                    chars[pos] = extra_moves[owner]
                if extra_root is not None and owner == extra_root:
                    chars[pos] = destination
            result.append("".join(chars))
        return result

    def evaluate(full):
        short = short_codes(full, order)
        hard1500_10000 = []
        hard3500_2000 = []
        for rank, i in enumerate(order[:3500], 1):
            code = full[i]
            wr = word_ranks.get(code)
            if not wr or code in FIXED:
                continue
            if rank <= 1500 and wr <= args.top1500_words:
                hard1500_10000.append(i)
            elif rank <= 3500 and wr <= args.top3500_words:
                hard3500_2000.append(i)
        return {
            "hard1500x10000": len(hard1500_10000),
            "hard3500x2000": len(hard3500_2000),
            "full1500": duplicates(full, order, 1500),
            "full3500": duplicates(full, order, 3500),
            "full6000": duplicates(full, order, 6000),
            "short1500": duplicates(short, order, 1500),
            "short3500": duplicates(short, order, 3500),
            "three1500": sum(len(short[i]) == 3 for i in order[:1500]),
            "three3500": sum(len(short[i]) == 3 for i in order[:3500]),
        }

    baseline = evaluate(make_codes())
    print("baseline", baseline)
    baseline_codes = make_codes()
    for rank, i in enumerate(order[:3500], 1):
        code = baseline_codes[i]
        wr = word_ranks.get(code)
        if 1500 < rank <= 3500 and wr and wr <= 2000 and code not in FIXED:
            print("expanded-hard", elements[i]["词"], rank, code, wr, owners[i])
    if args.inspect_only:
        return
    rows = []
    if args.swaps:
        focus = {"月", "亻", "土", "艹", "忄", "巾", "木", "田"}
        seen = set()
        for root_a in focus:
            if root_a not in root_keys:
                continue
            for root_b in root_keys:
                if root_a == root_b or root_keys[root_a] == root_keys[root_b]:
                    continue
                pair = tuple(sorted((root_a, root_b)))
                if pair in seen:
                    continue
                seen.add(pair)
                metric = evaluate(make_codes(extra_moves={
                    root_a: root_keys[root_b], root_b: root_keys[root_a],
                }))
                if metric["hard1500x10000"] or metric["hard3500x2000"]:
                    continue
                rows.append({"root": root_a, "from": root_keys[root_a],
                             "to": root_keys[root_b], "swap_root": root_b,
                             "swap_from": root_keys[root_b], **metric})
        rows.sort(key=lambda x: (
            x["hard3500x2000"], x["full3500"], x["short3500"],
            -x["three1500"], -x["three3500"], x["full6000"],
        ))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t")
            writer.writeheader(); writer.writerows(rows)
        print(f"feasible swaps={len(rows)} output={args.output}")
        for row in rows[:30]:
            print(row)
        return
    for root, source in root_keys.items():
        if args.root and root != args.root:
            continue
        for destination in KEYS:
            if destination == source:
                continue
            metric = evaluate(make_codes(root, destination))
            if metric["hard1500x10000"] or metric["hard3500x2000"]:
                continue
            rows.append({"root": root, "from": source, "to": destination, **metric})
    rows.sort(key=lambda x: (
        x["hard3500x2000"], x["full3500"], x["short3500"],
        -x["three1500"], -x["three3500"], x["full6000"],
    ))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t")
            writer.writeheader(); writer.writerows(rows)
    print(f"feasible={len(rows)} output={args.output}")
    for row in rows[:30]:
        print(row)


if __name__ == "__main__":
    main()
