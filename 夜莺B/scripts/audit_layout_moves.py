# -*- coding: utf-8 -*-
"""穷举固定布局的单主根搬移，快速筛选可行的局部改良。

第一阶段只计算可由码表直接得到的离散、词槽和静态负担指标；
组合当量留给 chai encode 对入围候选做最终复核。
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

import yaml


BASE = Path(__file__).resolve().parents[1]
KEYS = "abcdefghijklmnopqrstuvwxyz"
PINKY = set("qazp")
LEFT = set("qwertasdfgzxcvb")


def word_weight(rank: int) -> float:
    if rank <= 2000:
        return 1.0
    if rank <= 10000:
        return 0.5
    if rank <= 30000:
        return 0.2
    return 0.05


def load_targets():
    result = {}
    path = BASE / "work" / "lexicon" / "目标词库_四码位.tsv"
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            two = int(row["two_top_rank"]) if row["two_top_rank"] else None
            four = int(row["four_top_rank"]) if row["four_top_rank"] else None
            soft = (word_weight(two) if two else 0.0)
            soft += (word_weight(four) * 0.25 if four else 0.0)
            result[row["code"]] = {
                "soft": soft,
                "hard": two is not None and two <= 10000 and row["code"] not in {"wjhv", "iruu"},
            }
    return result


def duplicates(codes, order, top):
    counts = Counter(codes[i] for i in order[:top])
    dup = sum(n - 1 for n in counts.values() if n > 1)
    squared = sum((n - 1) ** 2 for n in counts.values() if n > 1)
    return dup, squared


def short_codes(full, order):
    """每个三码前缀的最高频项出三码，其余项保留全码。"""
    first = {}
    for i in order:
        first.setdefault(full[i][:3], i)
    return [code[:3] if first[code[:3]] == i else code for i, code in enumerate(full)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument("code", type=Path)
    parser.add_argument("--output", type=Path, default=BASE / "work" / "单根移动审计.tsv")
    parser.add_argument("--skip-baseline-check", action="store_true")
    args = parser.parse_args()

    elements = yaml.safe_load((BASE / "work" / "analysis_elements.yaml").read_text(encoding="utf-8"))
    root_cfg = yaml.safe_load((BASE / "work" / "根集.yaml").read_text(encoding="utf-8"))
    roots = list(root_cfg["roots"])
    mapping = yaml.safe_load(args.config.read_text(encoding="utf-8"))["form"]["mapping"]
    rows = [line.split("\t") for line in args.code.read_text(encoding="utf-8").splitlines()]
    if len(rows) != len(elements):
        raise ValueError(f"code/elements 行数不一致: {len(rows)} != {len(elements)}")

    frequencies = [int(x.get("频率", 0)) for x in elements]
    # 与 chai 一致：高频优先；同频保持 elements 原顺序。
    order = sorted(range(len(elements)), key=lambda i: -frequencies[i])
    targets = load_targets()

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

    base_full = [x[1] for x in rows]
    owners = []
    root_contribution = Counter()
    key_load = Counter()
    total_shape = 0
    for i, item in enumerate(elements):
        pair = []
        f = frequencies[i]
        for slot in item["元素序列"][2:4]:
            owner, key = trace(slot["element"])
            pair.append(owner if owner in roots else None)
            if isinstance(key, str) and key in KEYS:
                key_load[key] += f
                total_shape += f
            if owner in roots:
                root_contribution[owner] += f
        owners.append(pair)

    root_keys = {}
    for root in roots:
        _, key = trace(root)
        if isinstance(key, str) and key in KEYS:
            root_keys[root] = key

    def evaluate(root=None, destination=None):
        if root is None:
            full = base_full
        else:
            full = []
            for code, pair in zip(base_full, owners):
                chars = list(code)
                if pair[0] == root:
                    chars[2] = destination
                if pair[1] == root:
                    chars[3] = destination
                full.append("".join(chars))
        short = short_codes(full, order)
        hard = sum(1 for i in order[:1500]
                   if full[i] in targets and targets[full[i]]["hard"])
        soft = 0.0
        for rank, i in enumerate(order[:5000], 1):
            target = targets.get(full[i])
            if not target:
                continue
            factor = 1.0 if rank <= 1500 else 0.5 if rank <= 3500 else 0.2
            soft += target["soft"] * factor
        loads = key_load.copy()
        if root is not None:
            amount = root_contribution[root]
            loads[root_keys[root]] -= amount
            loads[destination] += amount
        shares = {k: loads[k] / total_shape * 100 for k in KEYS}
        return {
            "hard": hard,
            "full1500": duplicates(full, order, 1500)[0],
            "full3500": duplicates(full, order, 3500)[0],
            "full6000": duplicates(full, order, 6000)[0],
            "short1500": duplicates(short, order, 1500)[0],
            "short3500": duplicates(short, order, 3500)[0],
            "three1500": sum(len(short[i]) == 3 for i in order[:1500]),
            "three3500": sum(len(short[i]) == 3 for i in order[:3500]),
            "soft": soft,
            "pinky": sum(shares[k] for k in PINKY),
            "left": sum(shares[k] for k in LEFT),
            "peak": max(shares.values()),
            "peak_key": max(shares, key=shares.get),
        }

    baseline = evaluate()
    print("baseline", baseline)
    expected = {"hard": 0, "full1500": 0, "full3500": 21, "full6000": 193,
                "short1500": 0, "short3500": 3, "three1500": 1339, "three3500": 2636}
    mismatch = {k: (baseline[k], v) for k, v in expected.items() if baseline[k] != v}
    if mismatch and not args.skip_baseline_check:
        raise RuntimeError(f"基线未与 chai 指标对齐: {mismatch}")

    output = []
    for root, source in root_keys.items():
        for destination in KEYS:
            if destination == source:
                continue
            metric = evaluate(root, destination)
            if metric["hard"] or metric["full1500"] or metric["short1500"]:
                continue
            output.append({"root": root, "from": source, "to": destination,
                           "contribution": root_contribution[root] / total_shape * 100, **metric})

    # 优先找不损失核心离散、同时降低峰值/偏手/小指的移动。
    output.sort(key=lambda x: (
        x["full3500"] - baseline["full3500"],
        x["short3500"] - baseline["short3500"],
        -(x["three1500"] - baseline["three1500"]),
        -(x["three3500"] - baseline["three3500"]),
        x["full6000"] - baseline["full6000"],
        x["soft"] - baseline["soft"],
        x["peak"], abs(x["left"] - 50), x["pinky"],
    ))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(output[0]) if output else []
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        writer.writeheader(); writer.writerows(output)
    print(f"feasible moves: {len(output)} -> {args.output}")
    for row in output[:30]:
        print(row)


if __name__ == "__main__":
    main()
