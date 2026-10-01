"""全条件快速评分（numpy）：按引擎口径重算形码成本、四码、三简、p 占比、字词冲突、有效重码、虫鸟、换键，
实打三项用键对指法标记（同指大跨排 ms、小指干扰 pd、当量）按字频加权近似，再用已实测的方案校准。
score(lay) → (F, S, 指标)，F = 1000×门禁罚分 − S，与 neighborhood/proxy.py 同口径。"""
import json, sys, os, collections
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../neighborhood'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../tournament'))
import forces as FO
import n30_rank as R

ROOT = FO.ROOT; G = FO.G; KEYS = FO.KEYS; KI = FO.KI; N = FO.N
Y = json.load(open(ROOT / 'build/out/n30/yozakura.json'))['shape']
TOP = np.zeros(N, bool); TOP[[i for i in Y['top'] if i < N]] = True
REST = np.zeros(N, bool); REST[[i for i in Y['rest'] if i < N]] = True
FOUR = np.zeros(N, bool); FOUR[[i for i in Y['four_idx'] if i < N]] = True
SANI = np.zeros(N, bool); SANI[[i for i in Y['san_idx'] if i < N]] = True
fr = np.array(FO.fr, float); fixed = np.array(FO.fixed)
S1 = np.array([KI[s[1]] for s in FO.syl]); G1 = np.array(FO.g1); G2 = np.array(FO.g2)
C = json.load(open(ROOT / 'eval/box/combo.json'))
K27 = KEYS + ' '
FLAG = {f: np.array([[float(C[a + b][f]) for b in K27] for a in K27]) for f in ('ms', 'pd', 'eq')}
t1521 = np.zeros(N, bool); t1521[list(FO.T1521)] = True
t3571 = np.zeros(N, bool); t3571[list(FO.T3571)] = True
order = np.argsort(-fr, kind='stable')
WC = {}
for x in FO.WD:
    r = x['排名']; c = WC.setdefault(x['码'], [0, 0, 0]); c[0] += r <= 10000; c[1] += r <= 30000; c[2] += 1
META = FO.META; B = META['layout']
GB = FO.GI[next(g for g in G if '鸟' in META['groups'][g])]; GC = FO.GI[next(g for g in G if '虫' in META['groups'][g])]
SCORE = dict(R.SCORE); SCORE['字词冲突6万'] = (15, 631, 315); LOW = {'字词冲突6万': -1.5}
CAL_PATH = ROOT / 'construct/model_cal.json'
CAL = json.load(open(CAL_PATH)) if CAL_PATH.exists() else None
SPACE = 26


def raw(lay, act=None):
    """act：只计已加入的读音（逐批加入时用）。"""
    k = np.array([KI[lay[g]] for g in G]); k1, k2 = k[G1], k[G2]
    mask = FO.full_mask(lay)                       # 要打全码（无一二三简）
    if act is None:
        act = np.ones(N, bool)
    mask = mask & act
    nf = ~fixed & act; san = nf & ~mask
    e23 = FLAG['eq'][S1, k1]; e34 = FLAG['eq'][k1, k2]
    c = np.where(san, e23, (e23 + e34) / 2)
    m = {}
    sel = TOP & nf; m['top'] = c[sel].mean() if sel.any() else 0
    sel = REST & nf; m['rest'] = (c[sel] * fr[sel]).sum() / fr[sel].sum() if sel.any() else m['top']
    m['形码成本'] = 0.5 * m['top'] + 0.5 * m['rest']
    m['四码'] = int((FOUR & mask).sum()); m['三简'] = int((SANI & san).sum())
    if not (TOP & nf).any(): m['top'] = m['rest']; m['形码成本'] = m['rest']
    p = KI['p']; ww = fr * nf
    tt = (ww * np.where(san, 1, 2)).sum(); pp = (ww * ((k1 == p).astype(float) + (mask & (k2 == p)).astype(float))).sum()
    m['p占比'] = pp / tt
    # 实打近似：形码段键对（音码末键→首根、首根→空格/末根）按字频加权
    nxt = np.where(mask, k2, SPACE)
    tot = fr.sum()
    for f in ('ms', 'pd', 'eq'):
        m['f_' + f] = float(((FLAG[f][S1, k1] + FLAG[f][k1, nxt]) * ww).sum() / tot)
    # 字词冲突与有效重码（只看要打全码的读音）
    cl = [0, 0, 0, 0]; d1 = d3 = 0; seen = {}
    for i in np.nonzero(act)[0]:                    # 元素序即字频序
        if not mask[i]:
            continue                                    # 有一二三简的读音：全码位让位，不计重码、不计字词冲突
        code = FO.syl[i] + KEYS[k1[i]] + KEYS[k2[i]]
        sig = (G1[i], G2[i]); s = seen.get(code)
        if s is not None and any(x != sig for x in s):   # 实际选重：前面有签名不同、也必须打全码的读音
            d1 += t1521[i]; d3 += t3571[i]
        seen.setdefault(code, set()).add(sig)
        w_ = WC.get(code)
        if w_:
            if t1521[i]: cl[0] += w_[0] > 0; cl[1] += w_[1] > 0
            if t3571[i]: cl[2] += w_[0] > 0
            cl[3] += w_[2]
    m['撞码'] = cl; m['1521重'] = d1; m['3571重'] = d3
    m['虫鸟'] = int(k[GB] == k[GC]); m['换键根组'] = sum(lay[g] != B[g] for g in G)
    return m


def typing(m):
    x = [m['f_ms'], m['f_pd'], m['f_eq'], 1.0]
    return {t: float(np.dot(CAL[t], x)) for t in CAL}


def score(lay, act=None):
    m = raw(lay, act); t = typing(m)
    met = {'形码成本': m['形码成本'], 'p占比': m['p占比'], '撞码②': m['撞码'][1], '撞码③': m['撞码'][2], '三简': m['三简'],
           '换键根组': m['换键根组'], '小指干扰%': t['小指干扰%'], '同指大跨排%': t['同指大跨排%'], '键均当量': t['键均当量'],
           '字词冲突6万': m['撞码'][3]}
    S = 0.0
    for kk, (wt, zero, full) in SCORE.items():
        S += wt * max(LOW.get(kk, -0.5), min(1.2, (met[kk] - zero) / (full - zero)))
    pen = m['1521重'] + max(0, m['3571重'] - 9) + m['撞码'][0] + max(0, m['撞码'][2] - 5) + max(0, m['四码'] - 125) + m['虫鸟']
    return 1000 * pen - S, S, {**m, **t, 'pen': pen}


def calibrate():
    """用 n30 已实测（set0 实打）的方案校准实打三项。"""
    import glob
    X, Ys = [], []
    for p in glob.glob(str(ROOT / 'runs/n30*/*/n30eval.json')):
        ev = json.load(open(p, encoding='utf-8'))
        if 'layout' not in ev:
            continue
        m = raw(ev['layout']); X.append([m['f_ms'], m['f_pd'], m['f_eq'], 1.0])
        Ys.append([ev['实打'][t] for t in ('小指干扰%', '同指大跨排%', '键均当量')])
    X, Ys = np.array(X), np.array(Ys)
    cal = {}
    for j, t in enumerate(('小指干扰%', '同指大跨排%', '键均当量')):
        co, *_ = np.linalg.lstsq(X, Ys[:, j], rcond=None); pr = X @ co
        print(t, 'R²', round(1 - ((Ys[:, j] - pr) ** 2).sum() / ((Ys[:, j] - Ys[:, j].mean()) ** 2).sum(), 3), '样本', len(X))
        cal[t] = co.tolist()
    json.dump(cal, open(CAL_PATH, 'w'), ensure_ascii=False)


if __name__ == '__main__':
    calibrate()
