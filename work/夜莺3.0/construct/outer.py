"""外层：按当前布局判定谁打全码 → 重建力量项 → 力量迭代 → 逐组收敛 → 重复。"""
import json, sys, numpy as np, os
sys.path.insert(0, os.path.dirname(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../neighborhood'))
import forces as FO
import engine_eval as E
os.environ.setdefault('NB_INP', 'n30w')
from batch_eval import Worker
B = E.META['layout']; G = FO.G
gb = next(g for g in G if '鸟' in E.META['groups'][g]); gc = next(g for g in G if '虫' in E.META['groups'][g])
mutex = {gb: gc, gc: gb}
pull = np.zeros((FO.NG, 26))
for g in G:
    pull[FO.GI[g], FO.KI[B[g]]] = FO.P_['PULL']
w = Worker()
lay = dict(B)
for rnd in range(int(sys.argv[1]) if len(sys.argv) > 1 else 4):
    mask = FO.full_mask(lay)
    terms = FO.build_terms(mask)
    P, F = FO.run(iters=300, verbose=False, terms=terms)
    start = {g: FO.KEYS[int(np.argmax(P[FO.GI[g]]))] for g in G}
    lay, e = FO.icm(start, *terms, pull, mutex)
    r = w.score(lay)
    print(f"第{rnd + 1}轮 要打全码的读音{int(mask.sum())} 模型能量{e:.0f} 换键{sum(lay[g] != B[g] for g in G)} 形{r['cost']:.4f} p{r['p_share']:.3f} "
          f"撞{r['clash']} 重{r['excl'][2:]} 四{int(r['four_top'])} 三简{int(r['san'])} 失败{r['gates']}", flush=True)
    json.dump(lay, open(os.path.join(os.path.dirname(__file__), f'outer_r{rnd + 1}.json'), 'w'))
