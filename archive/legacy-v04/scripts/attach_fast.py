# -*- coding: utf-8 -*-
"""挂靠搜索（增量差分版）：附属根 = 评分层标签合并，全对搜索 + 贪心执行。

差分原理：把 J 拆成可加聚合量——
  零阶桶 (pp,a,b): n/sum/max → 计数损失 Σ(n-1)、频率损失 Σ(sum-max)、扣除 Σn(n-1)
  边际 (pp,a) 与 (pp,b): 计数 c → Σc(c-1)
合并 x→y 只影响含 x 的桶，逐桶差分即可，无需重扫全表。

用法: python attach_fast.py [--target 143] [--max-cost 1.0]
"""
import argparse
import io
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
WORK = BASE / "work"
sys.path.insert(0, str(BASE / "scripts"))
from score import load_phonetic_keys, load_entries
from greedy import load_charset

W_ZERO, W_D1 = 0.6, 0.02


class State:
    def __init__(self, entries):
        self.entries = entries
        self.total = sum(e[4] for e in entries) or 1
        self.zb = defaultdict(lambda: [0, 0, 0])   # (pp,a,b) -> [n, sum, max]
        self.m1 = defaultdict(int)                 # (pp,a)
        self.m2 = defaultdict(int)                 # (pp,b)
        self.by_root = defaultdict(list)           # 标签 -> entry idx 列表
        for i, (ch, pp, a, b, f) in enumerate(entries):
            self._add((pp, a, b), f)
            self.m1[(pp, a)] += 1
            self.m2[(pp, b)] += 1
            self.by_root[a].append(i)
            if b != a:
                self.by_root[b].append(i)
        self.labels = {}  # 原始标签 -> 当前标签（仅记录被合并者）

    def _add(self, k, f):
        v = self.zb[k]
        v[0] += 1
        v[1] += f
        if f > v[2]:
            v[2] = f

    @staticmethod
    def _bucket_cost(v):
        n, s, mx = v
        if n <= 1:
            return 0.0, 0.0, 0
        return float(n - 1), float(s - mx), n * (n - 1)

    def J(self):
        zc = zw = ded = 0
        for v in self.zb.values():
            c, w, d = self._bucket_cost(v)
            zc += c
            zw += w
            ded += d
        d1 = (sum(c*(c-1) for c in self.m1.values()) + sum(c*(c-1) for c in self.m2.values()) - ded) / 50
        return zw / self.total * 10000 + W_ZERO * zc + W_D1 * d1, int(zc), zw / self.total * 10000

    def merge_cost(self, x, y):
        """把标签 x 并入 y 的 ΔJ（不执行）。"""
        d_zc = d_zw = d_ded = 0.0
        # 受影响零阶桶：键含 x → 目标键
        touched = {}
        for i in self.by_root.get(x, ()):
            ch, pp, a, b, f = self.entries[i]
            a = self.labels.get(a, a) if a not in (x, y) else a
            # 用当前标签
        # 简化：直接扫 zb 中含 x 的键（桶数远小于条目数）
        moves = [k for k in self.zb if k[1] == x or k[2] == x]
        agg = {}
        for k in moves:
            nk = (k[0], y if k[1] == x else k[1], y if k[2] == x else k[2])
            v = self.zb[k]
            c, w, d = self._bucket_cost(v)
            d_zc -= c; d_zw -= w; d_ded -= d
            if nk in agg:
                t = agg[nk]
                t[0] += v[0]; t[1] += v[1]; t[2] = max(t[2], v[2])
            else:
                base = self.zb.get(nk)
                if base is not None:
                    c2, w2, d2 = self._bucket_cost(base)
                    d_zc -= c2; d_zw -= w2; d_ded -= d2
                    agg[nk] = [base[0] + v[0], base[1] + v[1], max(base[2], v[2])]
                else:
                    agg[nk] = list(v)
        for nk, v in agg.items():
            c, w, d = self._bucket_cost(v)
            d_zc += c; d_zw += w; d_ded += d
        # 边际
        d_m = 0
        for m in (self.m1, self.m2):
            for k in [k for k in m if k[1] == x]:
                c1 = m[k]
                c2 = m.get((k[0], y), 0)
                d_m += (c1 + c2) * (c1 + c2 - 1) - c1 * (c1 - 1) - c2 * (c2 - 1)
        d_d1 = (d_m - d_ded) / 50
        return d_zw / self.total * 10000 + W_ZERO * d_zc + W_D1 * d_d1

    def merge(self, x, y):
        moves = [k for k in self.zb if k[1] == x or k[2] == x]
        for k in moves:
            nk = (k[0], y if k[1] == x else k[1], y if k[2] == x else k[2])
            v = self.zb.pop(k)
            t = self.zb[nk]
            t[0] += v[0]; t[1] += v[1]; t[2] = max(t[2], v[2])
        for m in (self.m1, self.m2):
            for k in [k for k in m if k[1] == x]:
                m[(k[0], y)] += m.pop(k)
        self.by_root[y].extend(self.by_root.pop(x, ()))
        for k, v in list(self.labels.items()):
            if v == x:
                self.labels[k] = y
        self.labels[x] = y


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=143)
    ap.add_argument("--max-cost", type=float, default=1.0)
    a = ap.parse_args()

    phon = load_phonetic_keys(WORK / "seed.yaml")
    charset = load_charset()
    entries = load_entries(WORK / "v174_assembled.tsv", phon, charset)
    roots = [l.strip() for l in open(WORK / "seed_roots.txt", encoding="utf-8") if l.strip()]
    movable = [r for r in roots if r not in "123456"]
    st = State(entries)
    J0, z0, w0 = st.J()
    print(f"基线: J={J0:.2f} 零阶{z0} 加权{w0:.2f}bp; 主根 {len(roots)}")

    mains = set(roots)
    curJ = J0
    log = []
    while len(mains) > a.target:
        best = None
        for x in movable:
            if x not in mains:
                continue
            for y in mains:
                if y == x:
                    continue
                dJ = st.merge_cost(x, y)
                if best is None or dJ < best[0]:
                    best = (dJ, x, y)
        dJ, x, y = best
        if dJ > a.max_cost:
            print(f"最优挂靠 {x}→{y} 代价 +{dJ:.2f} 超阈值，停止于 {len(mains)} 主根")
            break
        st.merge(x, y)
        mains.discard(x)
        curJ += dJ
        log.append((x, y, dJ))
        Jn, zn, wn = st.J()
        print(f"挂靠 {x}→{y}: +{dJ:.2f} → J={Jn:.2f} 零阶{zn} 主根{len(mains)}")

    Jf, zf, wf = st.J()
    with open(WORK / "attachments.tsv", "w", encoding="utf-8") as f:
        f.write("附属根\t宿主\t代价ΔJ\n")
        for x, y, c in log:
            f.write(f"{x}\t{y}\t{c:.3f}\n")
    print(f"\n终态: 主根 {len(mains)} + 附属 {len(log)}; J={Jf:.2f} 零阶{zf} 加权{wf:.2f}bp")
    print(f"(对比: 1.0 J≈81.3/零阶100/5.0bp; 174根裸奔 J={J0:.2f})")


if __name__ == "__main__":
    main()
