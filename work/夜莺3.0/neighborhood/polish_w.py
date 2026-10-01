"""带 6 万词软约束：从起点逐步全扫精修，再反向撤回到最少换键，输出曲线。用法：NB_INP=n30w python polish_w.py <起点换键数(curve.json)> <名字>"""
import json, sys, itertools
import engine_eval as E
from batch_eval import Worker
from proxy import full, R
import os
MAXMOVE = int(os.environ.get('MAXMOVE', 999))
if 'MOVE_ZERO' in os.environ:                  # 作者 2026-10-01：换根约束放宽到 65
    R.SCORE['换键根组'] = (10, int(os.environ['MOVE_ZERO']), 0)

KEYS = 'abcdefghijklmnopqrstuvwxyz'
G = sorted(E.META['groups']); B = E.META['layout']
start = {c['moved']: c['layout'] for c in json.load(open('curve.json', encoding='utf-8'))}[int(sys.argv[1])]
name = sys.argv[2]
w = Worker(); cur = dict(start); r = full(w, cur)
log = open(f'{name}.log', 'w')
def say(*a):
    print(*a, flush=True); print(*a, file=log, flush=True)
def line(r):
    return (f"换键{r['moved']} S={r['S']:.2f} 罚{r['pen']} 冲突6万={r['clash'][3]} 撞{r['clash'][:3]} 形{r['cost']:.4f} p{r['p_share']:.3f} "
            f"重{r['excl'][2:]} 四{int(r['four_top'])} 三简{int(r['san'])} 大跨≈{r['typing']['同指大跨排%']:.3f} 小指≈{r['typing']['小指干扰%']:.3f} 键均≈{r['typing']['键均当量']:.4f}")
say('起点', line(r))
for step in range(1, 100):
    cands = []
    for g in G:
        for k in KEYS:
            if k != cur[g]:
                lay = dict(cur); lay[g] = k
                if sum(1 for x in G if lay[x] != B[x]) > MAXMOVE:
                    continue
                cands.append((full(w, lay)['F'] - r['F'], g, k))
    cands.sort()
    mv = [cands[0][1:]] if cands[0][0] < -1e-9 else None
    if mv is None:
        bp = None
        for (_, g1, k1), (_, g2, k2) in itertools.combinations(cands[:120], 2):
            if g1 != g2:
                lay = dict(cur); lay[g1] = k1; lay[g2] = k2
                if sum(1 for x in G if lay[x] != B[x]) > MAXMOVE:
                    continue
                d = full(w, lay)['F'] - r['F']
                if bp is None or d < bp[0]:
                    bp = (d, [(g1, k1), (g2, k2)])
        if bp is None or bp[0] >= -1e-9:
            say('精修结束'); break
        mv = bp[1]
    for g, k in mv:
        cur[g] = k
    r = full(w, cur)
    say(f"步{step} " + ' + '.join(f"{''.join(E.META['groups'][g][:2])} {B[g]}→{k}" for g, k in mv) + ' ' + line(r))
curve = [{'moved': r['moved'], 'S': r['S'], 'layout': dict(cur)}]
while True:
    best = None
    for g in G:
        if cur[g] != B[g]:
            lay = dict(cur); lay[g] = B[g]; rr = full(w, lay)
            if rr['pen'] == 0 and (best is None or rr['S'] > best[1]['S']):
                best = (g, rr, lay)
    if best is None:
        say('再撤就破门禁'); break
    g, r, cur = best
    curve.append({'moved': r['moved'], 'S': r['S'], 'layout': dict(cur)})
    say(f"撤回 {''.join(E.META['groups'][g][:2])} " + line(r))
json.dump(curve, open(f'{name}.json', 'w', encoding='utf-8'), ensure_ascii=False)
