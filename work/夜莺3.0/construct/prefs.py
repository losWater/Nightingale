"""逐读音加入、各根组更新键喜好（作者 2026-10-01 设想）。
初始：各组按键的自带当量（该键与其他键往返的平均当量）排喜好。
读音按字频从高到低分批加入；每批后每组依次按"已加入读音"上的全条件评分给 26 个键打分，改投最喜欢的键。
全部加入后再全量来回几遍到稳定。输出每组 26 键喜好排名与分差。
用法：python construct/prefs.py"""
import json, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import model as MD

G, KEYS, N = MD.G, MD.KEYS, MD.N
EQ = MD.FLAG['eq'][:26, :26]
ease = {KEYS[k]: (EQ[k].mean() + EQ[:, k].mean()) / 2 for k in range(26)}
key_order = sorted(KEYS, key=ease.get)
lay = {g: key_order[0] for g in G}                       # 一开始什么都不知道：都投自带当量最好的键
order = np.argsort(-MD.fr, kind='stable')
BATCH = [300, 600, 1000, 1521, 2500, 3571, 5000, 6500, N]
prefs = {}


def sweep(act, tag, groups=None, quiet=False):
    changed = 0
    for g in (groups or G):
        sc = {}
        for k in KEYS:
            l = dict(lay); l[g] = k
            sc[k] = MD.score(l, act)[0]
        best = min(sc, key=sc.get)
        prefs[g] = sorted(KEYS, key=sc.get), sc
        if best != lay[g]:
            lay[g] = best; changed += 1
    if quiet:
        return changed
    F, S, m = MD.score(lay, act)
    print(f"{tag} 改投{changed}组 S={S:.1f} 罚{m['pen']} 形{m['形码成本']:.4f} 三简{m['三简']} 四码{m['四码']} p{m['p占比']:.3f} "
          f"撞{m['撞码']} 重{m['1521重']}/{m['3571重']} 换键{m['换键根组']}", flush=True)
    return changed


MODE = sys.argv[1] if len(sys.argv) > 1 else 'syllable'
if MODE == 'syllable':
    # 一个音一个音放（作者 2026-10-01）：按音节综合字频从高到低，每次加入该音节的全部同音读音，
    # 只让该音节读音涉及的根组更新喜好
    by = {}
    for i in range(N):
        by.setdefault(MD.FO.syl[i], []).append(i)
    syls = sorted(by, key=lambda s_: -sum(MD.fr[i] for i in by[s_]))
    act = np.zeros(N, bool)
    for n, s_ in enumerate(syls, 1):
        act[by[s_]] = True
        touched = sorted({G[MD.G1[i]] for i in by[s_]} | {G[MD.G2[i]] for i in by[s_]})
        sweep(act, f'第{n}个音节 {s_}（{len(by[s_])}个读音）', groups=touched, quiet=n % 25 != 0)
else:
    for n in BATCH:
        act = np.zeros(N, bool); act[order[:n]] = True
        sweep(act, f'加入前{n}个读音')
for r in range(8):
    if not sweep(None, f'全量第{r + 1}遍'):
        break
out = {g: {'排名': prefs[g][0], '分': {k: round(float(prefs[g][1][k] - prefs[g][1][prefs[g][0][0]]), 2) for k in prefs[g][0]}} for g in G}
json.dump({'layout': lay, 'prefs': out}, open(MD.ROOT / f'construct/prefs_{MODE}.json', 'w', encoding='utf-8'), ensure_ascii=False)
