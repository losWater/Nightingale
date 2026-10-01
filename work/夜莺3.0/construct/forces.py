"""力量拉扯（作者 2026-10-01 设想）→ 每个根组的候选键。
数学上是平均场 / 软分配：P[g,k] = 根组 g 在键 k 上的倾向；每轮按别的组当前倾向算出"放在 k 上有多好"（力量场），
softmax 更新并加阻尼，温度逐步降低，直到稳定。力量只来自读音（按音节分组、组内幂律加权）和词：
  单组：音码末键→首根键 当量（常用字三简手感）；拉回 2.5 原键（老用户）。
  两两：同音节常用字首根同键 → 抢三简（软，很重）；首根键→末根键 当量（全码手感）；
        全码 = 词码 → 字词冲突（① 前1521×前1万、③ 前3571×前1万 为死亡值，其余软）；
  四元：同音节两字首根同键且末根同键 → 重码（前1521 为死亡值，前3571 重罚，其余轻罚）。
用法：python construct/forces.py
"""
import json, collections, math, sys
from pathlib import Path
import numpy as np
import yaml
ROOT = Path(__file__).resolve().parent.parent
L = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
INP = ROOT / 'build/out/n30'
E = yaml.load(open(INP / 'elements.yaml', encoding='utf-8'), Loader=L)
META = json.load(open(INP / 'meta.json', encoding='utf-8'))
G = sorted(META['groups']); GI = {g: i for i, g in enumerate(G)}; NG = len(G)
KEYS = 'abcdefghijklmnopqrstuvwxyz'; KI = {k: i for i, k in enumerate(KEYS)}; NK = 26
N = sum(1 for e in E if e['拼音'] != 'reserved')
C = json.load(open(ROOT / 'eval/box/combo.json'))
EQ = np.array([[C[a + b]['eq'] for b in KEYS] for a in KEYS])
T1521 = set(META['tier_indices']['1500']); T3571 = set(META['tier_indices']['3500'])

P_ = dict(S=2.58, H=10.0, LAM1=1.0, LAM2=0.5, DEATH=3000.0, DUP3=60.0, DUPX=1.0,
          CL1=3000.0, CL3=300.0, CL2=40.0, CL6=2.0, PULL=30.0)

# 读音
syl, g1, g2, fr, fixed = [], [], [], [], []
for e in E[:N]:
    s = e['元素序列']
    syl.append(s[0]['element'][2:] + s[1]['element'][2:]); g1.append(GI[s[2]['element']]); g2.append(GI[s[3]['element']])
    fr.append(e['频率']); fixed.append(bool(e.get('简码长度')))
by_syl = collections.defaultdict(list)
for i in range(N):
    by_syl[syl[i]].append(i)
w = np.zeros(N)
for s_, idx in by_syl.items():
    idx.sort(key=lambda i: -fr[i])
    z = sum((k + 1) ** -P_['S'] for k in range(len(idx))); tot = sum(fr[i] for i in idx)
    for k, i in enumerate(idx):
        w[i] = tot * (k + 1) ** -P_['S'] / z
w = w / w.sum() * 1e4
rank = {i: r for r, i in enumerate(sorted(range(N), key=lambda i: -fr[i]))}

# 词（虎码词库 6 万：常用 4 万 + 新码位 2 万；排名用于 ①②③ 分档）
WD = json.load(open(ROOT / 'data/inputs/虎码词库_字词避重6万词.json', encoding='utf-8'))
words_by_syl = collections.defaultdict(list)
for x in WD:
    words_by_syl[x['码'][:2]].append((KI[x['码'][2]], KI[x['码'][3]], x['排名']))


def full_mask(lay):
    """按布局判定哪些读音要打全码：同音节按字频先到先得三简（首根键相同只有最常用的拿到）。"""
    mask = np.zeros(N, bool)
    for s_, idx in by_syl.items():
        taken = set()
        for i in idx:                                       # idx 已按字频降序
            if fixed[i]:
                continue
            p = lay[G[g1[i]]]
            if p in taken:
                mask[i] = True
            else:
                taken.add(p)
    return mask


def build_terms(mask=None):
    U = np.zeros((NG, NK))
    C3 = np.zeros((NG, NG))
    M = collections.defaultdict(lambda: np.zeros((NK, NK)))
    for i in range(N):
        if fixed[i]:
            continue
        U[g1[i]] += P_['LAM1'] * w[i] * EQ[KI[syl[i][1]]]
        if mask is not None and not mask[i]:
            continue
        M[(g1[i], g2[i])] += P_['LAM2'] * w[i] * EQ
        for k3, k4, r in words_by_syl[syl[i]]:
            if i in T1521 and r <= 10000: c = P_['CL1']
            elif i in T3571 and r <= 10000: c = P_['CL3']
            elif i in T1521 and r <= 30000: c = P_['CL2']
            else: c = P_['CL6']
            M[(g1[i], g2[i])][k3, k4] += c
    D = []                                                   # 四元重码项 (a1,a2,b1,b2,权重)
    for s_, idx in by_syl.items():
        nf = [i for i in idx if not fixed[i]]
        for x in range(len(nf)):
            for y in range(x + 1, len(nf)):
                i, j = nf[x], nf[y]                          # i 比 j 常用
                if g1[i] != g1[j]:
                    C3[g1[i], g1[j]] += P_['H'] * w[j]; C3[g1[j], g1[i]] += P_['H'] * w[j]
                if (g1[i], g2[i]) == (g1[j], g2[j]) or (mask is not None and not mask[j]):
                    continue
                d = P_['DEATH'] if j in T1521 else P_['DUP3'] if j in T3571 else P_['DUPX']
                D.append((g1[i], g2[i], g1[j], g2[j], d))
    D = np.array(D)
    return U, C3, dict(M), D


def field(P, U, C3, M, D, pull):
    F = U + C3 @ P - pull
    for (a, b), m in M.items():
        if a == b:
            F[a] += np.diag(m)
        else:
            F[a] += m @ P[b]; F[b] += m.T @ P[a]
    a1, a2, b1, b2 = (D[:, c].astype(int) for c in range(4)); d = D[:, 4]
    A1 = np.where(a1 == b1, 1.0, (P[a1] * P[b1]).sum(1)); A2 = np.where(a2 == b2, 1.0, (P[a2] * P[b2]).sum(1))
    m1 = a1 != b1; m2 = a2 != b2
    np.add.at(F, a1[m1], (d * A2)[m1, None] * P[b1[m1]]); np.add.at(F, b1[m1], (d * A2)[m1, None] * P[a1[m1]])
    np.add.at(F, a2[m2], (d * A1)[m2, None] * P[b2[m2]]); np.add.at(F, b2[m2], (d * A1)[m2, None] * P[a2[m2]])
    return F


def run(iters=400, damp=0.5, seed=0, verbose=True, mask=None, terms=None):
    U, C3, M, D = terms or build_terms(mask)
    base = META['layout']
    pull = np.zeros((NG, NK))
    for g in G:
        pull[GI[g], KI[base[g]]] = P_['PULL']
    # 虫鸟互斥：用强斥力实现
    gb = GI[next(g for g in G if '鸟' in META['groups'][g])]; gc = GI[next(g for g in G if '虫' in META['groups'][g])]
    C3[gb, gc] += P_['DEATH']; C3[gc, gb] += P_['DEATH']
    rng = np.random.default_rng(seed)
    P = np.full((NG, NK), 1 / NK) + rng.random((NG, NK)) * 1e-3; P /= P.sum(1, keepdims=True)
    F = field(P, U, C3, M, D, pull)
    T0 = float(np.median(F.std(1))) * 2; T1 = T0 / 300
    for it in range(iters):
        T = T0 * (T1 / T0) ** (it / (iters - 1))
        F = field(P, U, C3, M, D, pull)
        Z = -(F - F.min(1, keepdims=True)) / T
        Q = np.exp(Z); Q /= Q.sum(1, keepdims=True)
        P = damp * P + (1 - damp) * Q
        if verbose and it % 50 == 0:
            ent = float(-(P * np.log(P + 1e-12)).sum(1).mean())
            print(f'迭代{it} 温度{T:.2f} 平均熵{ent:.2f} 已确定组(最大倾向>0.9) {int((P.max(1) > .9).sum())}', flush=True)
    return P, F


if __name__ == '__main__':
    P, F = run()
    out = {G[g]: {'键序': [KEYS[k] for k in np.argsort(F[g])[:8]], '力量场': {KEYS[k]: round(float(F[g, k]), 1) for k in range(NK)},
                  '倾向': {KEYS[k]: round(float(P[g, k]), 3) for k in np.argsort(-P[g])[:5]}} for g in range(NG)}
    json.dump(out, open(ROOT / 'construct/forces.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    np.save(ROOT / 'construct/forces_P.npy', P); np.save(ROOT / 'construct/forces_F.npy', F)


def energy(lay, U, C3, M, D, pull):
    """一热布局下的模型能量（越小越好），分项返回。"""
    k = np.array([KI[lay[g]] for g in G])
    e = {'单组当量': float(U[np.arange(NG), k].sum()), '拉回2.5': -float(pull[np.arange(NG), k].sum())}
    same = (k[:, None] == k[None, :])
    e['抢三简'] = float((C3 * same).sum() / 2)
    mt = 0.0
    for (a, b), m in M.items():
        mt += m[k[a], k[b]]
    e['全码当量+字词冲突'] = float(mt)
    a1, a2, b1, b2 = (D[:, c].astype(int) for c in range(4))
    hit = (k[a1] == k[b1]) & (k[a2] == k[b2])
    e['重码'] = float(D[hit, 4].sum())
    e['总'] = sum(e.values())
    return e


def icm(lay, U, C3, M, D, pull, mutex=None):
    """逐组取能量最低的键，直到不再变化（落子前的局部收敛）。"""
    lay = dict(lay); best = energy(lay, U, C3, M, D, pull)['总']
    changed = True
    while changed:
        changed = False
        for g in G:
            cur = lay[g]
            for kk in KEYS:
                if kk == cur or (mutex and mutex.get(g) and lay[mutex[g]] == kk):
                    continue
                lay[g] = kk; e = energy(lay, U, C3, M, D, pull)['总']
                if e < best - 1e-9:
                    best, cur, changed = e, kk, True
            lay[g] = cur
    return lay, best
