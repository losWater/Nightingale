"""从 2.5 出发的正向贪心：每步全扫 129 组 × 25 键，取 q 下降最多的一步；
单步无改进时，在单步前 150 名里两两组合找一对；每步后检查已做的改动能否撤回（不再必要的撤回）。
输出 forward.json / forward.log
"""
import json, sys, itertools
from pathlib import Path
import engine_eval as E
from batch_eval import Worker

KEYS = 'abcdefghijklmnopqrstuvwxyz'
G = sorted(E.META['groups']); B = E.META['layout']
w = Worker()
cur = dict(B)
r = w.score(cur)
path = [{'step': 0, 'move': None, 'n': 0, **{k: r[k] for k in ('q', 'cost', 'p_share', 'clash', 'excl', 'four_top', 'san', 'gates')}}]
print('起点 2.5 q', round(r['q'], 1), r['gates'], flush=True)
MAXSTEP = int(sys.argv[1]) if len(sys.argv) > 1 else 60


def moved():
    return [g for g in G if cur[g] != B[g]]


for step in range(1, MAXSTEP + 1):
    base_q = r['q']
    cands = []
    for g in G:
        for k in KEYS:
            if k == cur[g]:
                continue
            lay = dict(cur); lay[g] = k
            cands.append((w.score(lay)['q'] - base_q, g, k))
    cands.sort()
    best = cands[0]
    mv = [(best[1], best[2])]
    if best[0] >= 0:
        top = cands[:150]
        bp = None
        for (d1, g1, k1), (d2, g2, k2) in itertools.combinations(top, 2):
            if g1 == g2:
                continue
            lay = dict(cur); lay[g1] = k1; lay[g2] = k2
            d = w.score(lay)['q'] - base_q
            if bp is None or d < bp[0]:
                bp = (d, [(g1, k1), (g2, k2)])
        if bp is None or bp[0] >= 0:
            print('无改进，停止', flush=True); break
        mv = bp[1]
    for g, k in mv:
        cur[g] = k
    r = w.score(cur)
    # 撤回不再必要的改动
    for g in moved():
        lay = dict(cur); lay[g] = B[g]
        rr = w.score(lay)
        if rr['q'] <= r['q'] and not rr['gates']:
            cur = lay; r = rr; print('  撤回', g, flush=True)
    n = len(moved())
    path.append({'step': step, 'move': [(g, ''.join(E.META['groups'][g][:3]), B[g], k) for g, k in mv], 'n': n,
                 **{k: r[k] for k in ('q', 'cost', 'p_share', 'clash', 'excl', 'four_top', 'san', 'gates')}})
    print(f"步{step:2d} 换键{n:2d} {' + '.join(f'{g}{''.join(E.META['groups'][g][:3])} {B[g]}→{k}' for g, k in mv)} "
          f"q={r['q']:.1f} 形{r['cost']:.4f} p{r['p_share']:.3f} 撞{r['clash']} 重{r['excl'][2:]} 四{int(r['four_top'])} 三简{int(r['san'])} 失败{r['gates']}", flush=True)
    json.dump({'path': path, 'layout': cur}, open('forward.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
