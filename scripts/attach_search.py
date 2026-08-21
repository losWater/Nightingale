# -*- coding: utf-8 -*-
"""挂靠搜索：附属根不改拆分，只在评分层合并标签，因此可全对搜索。

1. 对每个可挂靠根 X，穷举宿主 Y，算标签合并后的 ΔJ，取最优宿主。
2. 贪心执行代价最小的挂靠（支持链条压平），直到主根数达标或代价超阈值。

用法: python attach_search.py [--target 143] [--max-cost 1.0]
"""
import argparse
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
BASE = Path(__file__).resolve().parent.parent
WORK = BASE / "work"
sys.path.insert(0, str(BASE / "scripts"))
from score import load_phonetic_keys, load_entries
from greedy import load_charset

W_ZERO, W_D1 = 0.6, 0.02


def compute_J(entries, remap):
    zero = defaultdict(list)
    m1 = defaultdict(int)
    m2 = defaultdict(int)
    total = 0
    for ch, pp, r3, r4, freq in entries:
        a, b = remap.get(r3, r3), remap.get(r4, r4)
        zero[(pp, a, b)].append(freq)
        m1[(pp, a)] += 1
        m2[(pp, b)] += 1
        total += freq
    zg = [sorted(v, reverse=True) for v in zero.values() if len(v) > 1]
    z_count = sum(len(v) - 1 for v in zg)
    z_w = sum(f for v in zg for f in v[1:]) / (total or 1)
    d1 = (sum(c*(c-1) for c in m1.values()) + sum(c*(c-1) for c in m2.values())) / 50 \
        - sum(len(v)*(len(v)-1) for v in zg) / 50
    return z_w * 10000 + W_ZERO * z_count + W_D1 * d1, z_count, z_w * 10000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=143)
    ap.add_argument("--max-cost", type=float, default=1.0)
    a = ap.parse_args()

    phon = load_phonetic_keys(WORK / "seed.yaml")
    charset = load_charset()
    entries = load_entries(WORK / "v174_assembled.tsv", phon, charset)
    roots = [l.strip() for l in open(WORK / "seed_roots.txt", encoding="utf-8") if l.strip()]
    # 笔画根不参与挂靠
    movable = [r for r in roots if r not in "123456"]

    remap = {}
    J0, z0, w0 = compute_J(entries, remap)
    print(f"基线: J={J0:.2f} 零阶{z0} 加权{w0:.2f}bp; 主根 {len(roots)}")

    # 只统计实际出现在首末位的根，未出现的根挂靠无代价可言（直接可挂任意处）
    used = set()
    for ch, pp, r3, r4, freq in entries:
        used.add(r3)
        used.add(r4)

    log = []
    mains = set(roots)
    while len(mains) > a.target:
        best = None
        hosts = [y for y in mains]
        for x in movable:
            if x not in mains:
                continue
            for y in hosts:
                if y == x or y not in mains:
                    continue
                trial = dict(remap)
                # x 挂到 y；已挂到 x 的一并改挂 y
                trial[x] = y
                for k, v in list(trial.items()):
                    if v == x:
                        trial[k] = y
                J, zc, zw = compute_J(entries, trial)
                if best is None or J < best[0]:
                    best = (J, x, y, zc, zw)
        J, x, y, zc, zw = best
        cost = J - (log[-1][3] if log else J0)
        if cost > a.max_cost:
            print(f"最优挂靠 {x}→{y} 代价 +{cost:.2f} 超过阈值 {a.max_cost}，停止于 {len(mains)} 主根")
            break
        remap[x] = y
        for k, v in list(remap.items()):
            if v == x:
                remap[k] = y
        mains.discard(x)
        log.append((x, y, cost, J, zc, zw))
        print(f"挂靠 {x}→{y}: 代价+{cost:.2f} → J={J:.2f} 零阶{zc} 主根{len(mains)}")

    with open(WORK / "attachments.tsv", "w", encoding="utf-8") as f:
        f.write("附属根\t宿主\t代价ΔJ\n")
        for x, y, cost, *_ in log:
            f.write(f"{x}\t{y}\t{cost:.3f}\n")
    Jf, zf, wf = compute_J(entries, remap)
    print(f"\n终态: 主根 {len(mains)} + 附属 {len(remap)}; J={Jf:.2f} 零阶{zf} 加权{wf:.2f}bp")
    print(f"(对比: 1.0 J≈81.3/零阶100/5.0bp; 174根裸奔 J={J0:.2f})")


if __name__ == "__main__":
    main()
