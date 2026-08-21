# -*- coding: utf-8 -*-
"""B 阶段贪心循环：逐根试加/试删，重拆参照字集，按复合目标挑最优。

目标 J = 加权零阶损失(bp) + W_ZERO*零阶选重数 + W_D1*一阶估计
（bp = 万分点。越小越好；Δ<阈值 时停止）

用法:
  python greedy.py --rounds 8 --mode add        # 只加根
  python greedy.py --rounds 4 --mode swap       # 每轮先加最优再删最差
"""
import argparse
import io
import json
import subprocess
import sys
import tempfile
import shutil
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parent.parent
WORK = BASE / "work"
CHARSET = BASE / "data/jdhe/简单鹤V1.0纯单版.txt"
BUN = r"C:\Users\asus\.bun\bin\bun.exe"

W_ZERO = 0.6   # 每条零阶选重折合 bp
W_D1 = 0.02    # 每点一阶估计折合 bp

sys.path.insert(0, str(BASE / "scripts"))
from score import load_phonetic_keys, load_entries  # noqa: E402

STROKE_FOLD = {"一": "1", "丨": "2", "丿": "3", "丶": "4", "乙": "5"}


def load_charset():
    cs = set()
    for line in open(CHARSET, encoding="utf-8-sig"):
        p = line.rstrip("\n").split("\t")
        if p and len(p[0]) == 1:
            cs.add(p[0])
    return cs


def make_config(base_cfg, roots, path):
    cfg = json.loads(json.dumps(base_cfg))  # deep copy
    mapping = {}
    for k, v in cfg["form"]["mapping"].items():
        k = str(k)
        if k.startswith("szm-") or k.startswith("mzm-"):
            mapping[k] = v
    for i, r in enumerate(roots):
        mapping[r] = "abcdefghijklmnostuvwxyz"[i % 23]
    mapping["6"] = {"element": "5"}
    cfg["form"]["mapping"] = mapping
    yaml.safe_dump(cfg, open(path, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False, width=10000)


def evaluate(base_cfg, roots, tag, phon, charset, tmpdir):
    cfgp = Path(tmpdir) / f"c_{tag}.yaml"
    outp = Path(tmpdir) / f"o_{tag}.tsv"
    make_config(base_cfg, roots, cfgp)
    try:
        r = subprocess.run([BUN, str(BASE / "scripts/assemble.ts"), str(cfgp), str(outp), str(CHARSET)],
                           capture_output=True, timeout=120)
        if r.returncode != 0:
            return None
        entries = load_entries(outp, phon, charset)
        if len(entries) < 8000:
            return None
        zero = defaultdict(list)
        for ch, pp, r3, r4, freq in entries:
            zero[(pp, r3, r4)].append(freq)
        zg = {k: sorted(v, reverse=True) for k, v in zero.items() if len(v) > 1}
        z_count = sum(len(v) - 1 for v in zg.values())
        total = sum(e[4] for e in entries) or 1
        z_w = sum(f for v in zg.values() for f in v[1:]) / total
        m1, m2 = defaultdict(int), defaultdict(int)
        for ch, pp, r3, r4, freq in entries:
            m1[(pp, r3)] += 1
            m2[(pp, r4)] += 1
        d1 = (sum(c * (c - 1) for c in m1.values()) + sum(c * (c - 1) for c in m2.values())) / 50 \
            - sum(len(v) * (len(v) - 1) for v in zg.values()) / 50
        J = z_w * 10000 + W_ZERO * z_count + W_D1 * d1
        return {"J": J, "zero": z_count, "zero_w_bp": z_w * 10000, "d1": d1}
    except Exception:
        return None


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--mode", choices=["add", "drop", "swap"], default="add")
    ap.add_argument("--min-gain", type=float, default=0.5, help="J 改善阈值(bp)")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--roots", default="work/seed_roots.txt")
    ap.add_argument("--pool-min", type=float, default=1.0, help="候选池最低票数")
    a = ap.parse_args()

    base_cfg = yaml.safe_load(open(WORK / "seed.yaml", encoding="utf-8"))
    phon = load_phonetic_keys(WORK / "seed.yaml")
    charset = load_charset()
    roots = [l.strip() for l in open(BASE / a.roots, encoding="utf-8") if l.strip()]

    pool = []
    for r in [l.rstrip("\n").split("\t") for l in open(WORK / "vote_matrix.tsv", encoding="utf-8")][1:]:
        c = STROKE_FOLD.get(r[0], r[0])
        if float(r[2]) >= a.pool_min and c not in roots and c not in pool:
            pool.append(c)
    print(f"起点: {len(roots)} 根; 候选池: {len(pool)}; 模式: {a.mode}")

    tmpdir = tempfile.mkdtemp(prefix="greedy_")
    try:
        cur = evaluate(base_cfg, roots, "base", phon, charset, tmpdir)
        print(f"当前 J={cur['J']:.2f} (零阶 {cur['zero']}, 加权 {cur['zero_w_bp']:.2f}bp, D1 {cur['d1']:.0f})")
        log = open(WORK / "greedy_log.tsv", "a", encoding="utf-8")

        for rnd in range(1, a.rounds + 1):
            actions = []
            if a.mode in ("add", "swap"):
                actions += [("+", c) for c in pool]
            if a.mode in ("drop", "swap"):
                actions += [("-", c) for c in roots if c not in "123456"]

            def run(act):
                op, c = act
                rs = roots + [c] if op == "+" else [x for x in roots if x != c]
                tag = f"{rnd}_{op}{ord(c[0]):x}"
                return act, evaluate(base_cfg, rs, tag, phon, charset, tmpdir)

            results = []
            with ThreadPoolExecutor(max_workers=a.jobs) as ex:
                for act, res in ex.map(run, actions):
                    if res:
                        results.append((act, res))
            results.sort(key=lambda x: x[1]["J"])
            print(f"\n-- 第{rnd}轮 top6 --")
            for (op, c), res in results[:6]:
                print(f"  {op}{c}: J={res['J']:.2f} (Δ{res['J']-cur['J']:+.2f}) 零阶{res['zero']} 加权{res['zero_w_bp']:.2f}bp D1 {res['d1']:.0f}")
            (op, best), best_res = results[0]
            gain = cur["J"] - best_res["J"]
            if gain < a.min_gain:
                print(f"最优改善 {gain:.2f}bp < 阈值 {a.min_gain}，停止")
                break
            if op == "+":
                roots.append(best)
                pool.remove(best)
            else:
                roots.remove(best)
                pool.append(best)
            cur = best_res
            log.write(f"{rnd}\t{op}{best}\t{cur['J']:.3f}\t{cur['zero']}\t{cur['zero_w_bp']:.3f}\t{cur['d1']:.1f}\t{len(roots)}\n")
            log.flush()
            # 每轮落盘，进程被杀也不丢战果
            open(BASE / a.roots, "w", encoding="utf-8").write("\n".join(roots))
            print(f"√ 采纳 {op}{best} → {len(roots)} 根, J={cur['J']:.2f}")

        open(BASE / a.roots, "w", encoding="utf-8").write("\n".join(roots))
        print(f"\n最终 {len(roots)} 根已写回 {a.roots}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
