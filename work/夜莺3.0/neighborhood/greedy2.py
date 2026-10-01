"""以正式赛总分近似为目标的逐步全扫。用法：python greedy2.py <起点: 25|champ> <名字>"""
import json, sys, itertools
import engine_eval as E
from batch_eval import Worker
from proxy import full

KEYS = 'abcdefghijklmnopqrstuvwxyz'
G = sorted(E.META['groups']); B = E.META['layout']
start, name = sys.argv[1], sys.argv[2]
w = Worker()
cur = dict(B) if start == '25' else E.champion()
r = full(w, cur)
log = open(f'{name}.log', 'w')
def say(*a):
    print(*a, flush=True); print(*a, file=log, flush=True)
def line(r):
    return (f"S={r['S']:.2f} 罚{r['pen']} 形{r['cost']:.4f} p{r['p_share']:.3f} 撞{r['clash']} 重{r['excl'][2:]} 四{int(r['four_top'])} "
            f"三简{int(r['san'])} 大跨≈{r['typing']['同指大跨排%']:.3f} 小指≈{r['typing']['小指干扰%']:.3f} 键均≈{r['typing']['键均当量']:.4f}")
say('起点', start, '换键', r['moved'], line(r))
path = [{'step': 0, 'move': None, 'layout': dict(cur), 'S': r['S'], 'pen': r['pen'], 'moved': r['moved']}]
for step in range(1, 80):
    cands = []
    for g in G:
        for k in KEYS:
            if k != cur[g]:
                lay = dict(cur); lay[g] = k
                cands.append((full(w, lay)['F'] - r['F'], g, k))
    cands.sort()
    mv = [cands[0][1:]] if cands[0][0] < -1e-9 else None
    if mv is None:
        bp = None
        for (d1, g1, k1), (d2, g2, k2) in itertools.combinations(cands[:120], 2):
            if g1 != g2:
                lay = dict(cur); lay[g1] = k1; lay[g2] = k2
                d = full(w, lay)['F'] - r['F']
                if bp is None or d < bp[0]:
                    bp = (d, [(g1, k1), (g2, k2)])
        if bp[0] >= -1e-9:
            say('无改进，停止'); break
        mv = bp[1]
    for g, k in mv:
        cur[g] = k
    r = full(w, cur)
    say(f"步{step:2d} 换键{r['moved']:2d} " + ' + '.join(f"{g}{''.join(E.META['groups'][g][:3])} {B[g]}→{k}" for g, k in mv) + ' ' + line(r))
    path.append({'step': step, 'move': mv, 'layout': dict(cur), 'S': r['S'], 'pen': r['pen'], 'moved': r['moved']})
    json.dump(path, open(f'{name}.json', 'w', encoding='utf-8'), ensure_ascii=False)
