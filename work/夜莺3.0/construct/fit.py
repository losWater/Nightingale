"""用真实评分拟合力量模型各分量的权重（作者 2026-10-01 同意的第一条路）。
样本：已知方案 + 256 组退火结果为起点，随机挪 1–12 组；真实评分 = 批量评分器的 F（门禁罚分×1000 − 近似正式赛总分，含 6 万词软约束）。
特征：在一热布局上精确计算的力量分量（有简码的字不计字词冲突和全码重码）。
"""
import json, sys, os, random, collections
import numpy as np
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../neighborhood'))
os.environ.setdefault('NB_INP', 'n30w')
import forces as FO
import engine_eval as E
from batch_eval import Worker
from proxy import full

G = FO.G; B = E.META['layout']; KEYS = FO.KEYS
# 词码 → 各档词数
WC = collections.defaultdict(lambda: np.zeros(3))
for x in FO.WD:
    r = x['排名']; WC[x['码']] += [r <= 10000, r <= 30000, 1]
syl1 = np.array([FO.KI[s[1]] for s in FO.syl]); G1 = np.array(FO.g1); G2 = np.array(FO.g2)
fixed = np.array(FO.fixed); w = FO.w
t1521 = np.zeros(FO.N, bool); t1521[list(FO.T1521)] = True
t3571 = np.zeros(FO.N, bool); t3571[list(FO.T3571)] = True
order = np.argsort(-np.array(FO.fr))
NAMES = ['音码→首根当量', '首根→末根当量(全码)', '没拿到三简的权重', '前1521打全码数', '前1521重码', '前3571重码', '其余重码',
         '撞①', '撞②', '撞③', '6万冲突', 'p键使用', '换键数', '虫鸟同键']


def feats(lay):
    k = np.array([FO.KI[lay[g]] for g in G])
    k1, k2 = k[G1], k[G2]
    mask = FO.full_mask(lay)
    nf = ~fixed
    f = np.zeros(len(NAMES))
    f[0] = (w * FO.EQ[syl1, k1] * nf).sum()
    f[1] = (w * FO.EQ[k1, k2] * mask).sum()
    f[2] = (w * mask).sum()
    f[3] = (mask & t1521).sum()
    seen = {}
    for i in order:
        if not mask[i]:
            continue
        code = FO.syl[i] + KEYS[k1[i]] + KEYS[k2[i]]
        sig = (FO.g1[i], FO.g2[i])
        if code in seen and any(s != sig for s in seen[code]):
            f[4 + (0 if t1521[i] else 1 if t3571[i] else 2)] += 1
        seen.setdefault(code, set()).add(sig)
        if code in WC:
            c = WC[code]
            if t1521[i]: f[7] += c[0] > 0; f[8] += c[1] > 0
            if t3571[i]: f[9] += c[0] > 0
            f[10] += c[2]
    p = FO.KI['p']
    f[11] = (w * nf * ((k1 == p).astype(float) + mask * (k2 == p))).sum()
    f[12] = sum(lay[g] != B[g] for g in G)
    gb = next(g for g in G if '鸟' in E.META['groups'][g]); gc = next(g for g in G if '虫' in E.META['groups'][g])
    f[13] = lay[gb] == lay[gc]
    return f


def samples(n_per=150, seed=1):
    rng = random.Random(seed)
    c = {x['moved']: x['layout'] for x in json.load(open(E.ROOT / 'neighborhood/curve.json'))}
    w65 = {x['moved']: x['layout'] for x in json.load(open(E.ROOT / 'neighborhood/w65.json'))}
    starts = [('2.5', B), ('冠军', E.champion())] + [(f'NB{n}', c[n]) for n in (40, 46, 57)] + [(f'W{n}', w65[n]) for n in (47, 55, 63)]
    import glob
    for p in sorted(glob.glob(str(E.ROOT / 'runs/n30/*/n30eval.json')))[::8]:
        ev = json.load(open(p, encoding='utf-8'))
        if 'layout' in ev:
            starts.append((Path_name(p), ev['layout']))
    out = []
    for name, lay0 in starts:
        out.append((name, dict(lay0)))
        for _ in range(n_per):
            lay = dict(lay0)
            for g in rng.sample(G, rng.choice([1, 2, 3, 5, 8, 12])):
                lay[g] = rng.choice(KEYS)
            out.append((name, lay))
    return out


def Path_name(p):
    return os.path.basename(os.path.dirname(p))


if __name__ == '__main__':
    wk = Worker()
    S = samples()
    X, y, grp, rows = [], [], [], []
    for name, lay in S:
        r = full(wk, lay)
        X.append(feats(lay)); y.append(r['F']); grp.append(name)
    X, y = np.array(X), np.array(y)
    np.savez(E.ROOT / 'construct/fit_data.npz', X=X, y=y, grp=np.array(grp))
    print('样本', len(y), '起点', len(set(grp)))
