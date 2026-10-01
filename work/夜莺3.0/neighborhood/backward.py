"""从精修后的冠军反向撤回：每轮撤回一个让近似总分掉得最少、且不破坏门禁的改动，画出“换键数—总分”曲线。"""
import json
import engine_eval as E
from batch_eval import Worker
from proxy import full

G = sorted(E.META['groups']); B = E.META['layout']
w = Worker()
cur = json.load(open('gch.json', encoding='utf-8'))[-1]['layout']
r = full(w, cur)
curve = [{'moved': r['moved'], 'S': r['S'], 'layout': dict(cur), 'reverted': None}]
print(r['moved'], round(r['S'], 2), flush=True)
while True:
    best = None
    for g in G:
        if cur[g] == B[g]:
            continue
        lay = dict(cur); lay[g] = B[g]
        rr = full(w, lay)
        if rr['pen'] == 0 and (best is None or rr['S'] > best[1]['S']):
            best = (g, rr, lay)
    if best is None:
        print('再撤回任何一组都会破坏门禁，停止'); break
    g, r, cur = best
    curve.append({'moved': r['moved'], 'S': r['S'], 'layout': dict(cur), 'reverted': g})
    print(r['moved'], round(r['S'], 2), '撤回', g, ''.join(E.META['groups'][g][:3]), flush=True)
json.dump(curve, open('curve.json', 'w', encoding='utf-8'), ensure_ascii=False)
