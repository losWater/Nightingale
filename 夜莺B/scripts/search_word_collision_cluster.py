# -*- coding: utf-8 -*-
"""对五组扩展硬词撞做受限多根束搜索，不改动其他字根。"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
import yaml


BASE = Path(__file__).resolve().parents[1]
KEYS = "abcdefghijklmnopqrstuvwxyz"
FIXED_CODES = {"wjhv", "iruu"}
GROUPS = [
    ("肿", ("月",)),
    ("蔬", ("艹",)),
    ("仕", ("亻", "土")),
    ("怖", ("忄", "巾")),
    ("柚", ("木", "田")),
]


def code_id(code: str) -> int:
    value = 0
    for char in code:
        value = value * 26 + ord(char) - 97
    return value


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", type=Path)
    ap.add_argument("code", type=Path)
    ap.add_argument("--move", action="append", default=[])
    ap.add_argument("--width", type=int, default=300)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    elements = yaml.safe_load((BASE / "work" / "analysis_elements.yaml").read_text(encoding="utf-8"))
    roots = set(yaml.safe_load((BASE / "work" / "根集.yaml").read_text(encoding="utf-8"))["roots"])
    mapping = yaml.safe_load(args.config.read_text(encoding="utf-8"))["form"]["mapping"]
    raw = [x.split("\t")[1] for x in args.code.read_text(encoding="utf-8").splitlines()]
    initial = dict(spec.split("=", 1) for spec in args.move)

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

    root_keys = {}
    for root in roots:
        _, key = trace(root)
        if root in initial:
            key = initial[root]
        if isinstance(key, str) and key in KEYS:
            root_keys[root] = key

    owners = []
    baseline_strings = []
    for item, code in zip(elements, raw):
        chars = list(code)
        pair = []
        for pos, slot in zip((2, 3), item["元素序列"][2:4]):
            owner, _ = trace(slot["element"])
            pair.append(owner if owner in roots else None)
            if owner in initial:
                chars[pos] = initial[owner]
        owners.append(pair)
        baseline_strings.append("".join(chars))

    base = np.array([[ord(c) - 97 for c in code] for code in baseline_strings], dtype=np.int16)
    masks = {root: [(i, pos) for i, pair in enumerate(owners) for pos, owner in zip((2, 3), pair)
                    if owner == root] for root in roots}
    order = np.array(sorted(range(len(elements)), key=lambda i: -int(elements[i].get("频率", 0))), dtype=np.int32)

    word_rank = np.zeros(26 ** 4, dtype=np.int32)
    with (BASE / "work" / "lexicon" / "目标词库_四码位.tsv").open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["two_top_rank"]:
                word_rank[code_id(row["code"])] = int(row["two_top_rank"])
    fixed_ids = {code_id(x) for x in FIXED_CODES}

    def build(state):
        arr = base.copy()
        for root, key in state:
            value = ord(key) - 97
            for i, pos in masks[root]:
                arr[i, pos] = value
        return arr

    def dup(ids, top):
        _, counts = np.unique(ids[order[:top]], return_counts=True)
        return int(np.maximum(counts - 1, 0).sum())

    def metric(state):
        arr = build(state)
        wide = arr.astype(np.int32)
        ids = ((wide[:, 0] * 26 + wide[:, 1]) * 26 + wide[:, 2]) * 26 + wide[:, 3]
        ranks = word_rank[ids]
        fixed = np.isin(ids, list(fixed_ids))
        hard_old = int(((ranks[order[:1500]] > 0) & (ranks[order[:1500]] <= 10000)
                        & ~fixed[order[:1500]]).sum())
        band = order[1500:3500]
        hard_new = int(((ranks[band] > 0) & (ranks[band] <= 2000) & ~fixed[band]).sum())

        prefixes = wide[:, 0] * 26 * 26 + wide[:, 1] * 26 + wide[:, 2]
        ordered_prefix = prefixes[order]
        _, first_pos = np.unique(ordered_prefix, return_index=True)
        winners = np.zeros(len(elements), dtype=bool)
        winners[order[first_pos]] = True
        short_ids = ids + 26 ** 4
        short_ids[winners] = prefixes[winners]
        result = {
            "hard_old": hard_old, "hard_new": hard_new,
            "full1500": dup(ids, 1500), "full3500": dup(ids, 3500), "full6000": dup(ids, 6000),
            "short1500": dup(short_ids, 1500), "short3500": dup(short_ids, 3500),
            "three1500": int(winners[order[:1500]].sum()),
            "three3500": int(winners[order[:3500]].sum()),
        }
        # 中间层容许暂时违反硬约束，但强烈偏好接近最终可行域。
        result["score"] = (
            hard_old * 2_000_000 + hard_new * 500_000
            + result["full1500"] * 2_000_000 + result["short1500"] * 2_000_000
            + result["full3500"] * 1500 + result["short3500"] * 1200
            + result["full6000"] * 20
            - result["three1500"] * 40 - result["three3500"] * 5
        )
        return result

    beam = [(tuple(), metric(tuple()))]
    print("baseline", beam[0][1], flush=True)
    for depth, (label, alternatives) in enumerate(GROUPS, 1):
        candidates = {}
        for state, _ in beam:
            used = {root for root, _ in state}
            for root in alternatives:
                if root in used:
                    continue
                for key in KEYS:
                    if key == root_keys[root]:
                        continue
                    next_state = tuple(sorted(state + ((root, key),)))
                    if next_state in candidates:
                        continue
                    candidates[next_state] = metric(next_state)
        ranked = sorted(candidates.items(), key=lambda x: x[1]["score"])
        # 留一部分按硬撞数分桶的多样性，避免补偿路径在中间层被全剪掉。
        selected = ranked[:args.width]
        beam = selected
        print(f"depth={depth} target={label} candidates={len(ranked)} best={beam[0]}", flush=True)

    final = sorted(beam, key=lambda x: (
        x[1]["hard_old"], x[1]["hard_new"], x[1]["full1500"], x[1]["short1500"],
        x[1]["full3500"], x[1]["short3500"], -x[1]["three1500"],
        -x[1]["three3500"], x[1]["full6000"],
    ))
    rows = []
    for state, met in final:
        rows.append({"moves": " ".join(f"{r}:{root_keys[r]}>{k}" for r, k in state), **met})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader(); writer.writerows(rows)
    print("final", final[:10], flush=True)


if __name__ == "__main__":
    main()
