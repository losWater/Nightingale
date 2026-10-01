"""冠军改动逐个撤回 + 逐步撤回（反向贪心）。q = 引擎目标 − 换键代价（越小越好）。
输出 neighborhood/revert.json
"""
import json, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import engine_eval as E

G = E.META['groups']; B = E.META['layout']
champ = E.champion()
moves = [k for k in G if champ[k] != B[k]]
pool = ThreadPoolExecutor(6)


def with_reverted(rev):
    lay = dict(champ)
    for k in rev:
        lay[k] = B[k]
    return lay


base = E.score(champ)
print('冠军 q', round(base['q'], 1), '门禁失败', base['gates'], flush=True)
single = dict(zip(moves, pool.map(lambda k: E.score(with_reverted([k])), moves)))
out = {'base': base, 'single': {k: {**v, 'dq': v['q'] - base['q']} for k, v in single.items()}}
for k in sorted(moves, key=lambda k: single[k]['q']):
    v = single[k]
    print(f"{k} {''.join(G[k][:4]):<8} {champ[k]}→{B[k]} 撤回 Δq={v['q'] - base['q']:+8.1f} 形{v['cost']:.4f} p{v['p_share']:.3f} 撞{v['clash']} 重{v['excl'][2:]} 四{int(v['four_top'])} 失败{v['gates']}", flush=True)

# 反向贪心：每轮撤回一个使 q 增加最少的改动（优先保持门禁）
rev, path, cur = [], [], base
left = list(moves)
while left:
    res = list(pool.map(lambda k: (k, E.score(with_reverted(rev + [k]))), left))
    res.sort(key=lambda kv: (bool(kv[1]['gates']), kv[1]['q']))
    k, v = res[0]
    rev.append(k); left.remove(k)
    path.append({'reverted': k, 'kept': len(left), 'q': v['q'], 'cost': v['cost'], 'p': v['p_share'], 'clash': v['clash'],
                 'excl': v['excl'], 'four': v['four_top'], 'san': v['san'], 'gates': v['gates']})
    print(f"保留{len(left):2d} 撤回 {k} {''.join(G[k][:3])} q={v['q']:.1f} 形{v['cost']:.4f} p{v['p_share']:.3f} 撞{v['clash']} 重{v['excl'][2:]} 四{int(v['four_top'])} 三简{int(v['san'])} 失败{v['gates']}", flush=True)
    out['path'] = path
    json.dump(out, open(Path(__file__).parent / 'revert.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
