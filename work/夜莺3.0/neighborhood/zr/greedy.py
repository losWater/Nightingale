"""从 NB46 出发、自然码输入，逐步全扫：每步走一个最好的根组换键（无改进时试两步组合），记录曲线。
F = 1000×门禁违例 + 1000×形码成本 + 撞② + 10×(大跨≈ + 小指≈) − 0.01×三简 + 5×(3600−三简)⁺ + 前3571选重 + 1667×(p占比−0.04)⁺（越小越好；p 项与引擎 p_weight/shape_cost 同比例）。
用法：../../.venv/bin/python greedy.py [最多步数] [起点（anneal_layouts.json 中的名字）] [输出名]
精修版（2026-10-13）：另加 前3571选重×2、(四码−120)⁺×0.5，以保住门禁余量。"""
import itertools, json, sys
import common as C
KEYS = 'abcdefghijklmnopqrstuvwxyz'
MAXSTEP = int(sys.argv[1]) if len(sys.argv) > 1 else 40
START = sys.argv[2] if len(sys.argv) > 2 else None
OUT = sys.argv[3] if len(sys.argv) > 3 else 'greedy'


def F(r):
    t = r['typing']
    return (1000 * r['pen'] + 1000 * r['cost'] + r['clash'][1]
            + 10 * (t['同指大跨排%'] + t['小指干扰%']) - 0.01 * r['san']
            + 5 * max(0, 3600 - r['san']) + r['excl'][3] + 1667 * max(0, r['p_share'] - 0.04)
            + (2 * r['excl'][3] + 0.5 * max(0, r['four_top'] - 120) if START else 0))


w = C.Worker(); cur = dict(json.load(open('anneal_layouts.json', encoding='utf-8'))[START]) if START else dict(C.B); r = C.score(w, cur); f = F(r)
log = open(f'{OUT}.log', 'w')
def say(*a):
    print(*a, flush=True); print(*a, file=log, flush=True)
say('起点', f'F={f:.2f}', C.line(r))
curve = [{'step': 0, 'F': f, 'layout': dict(cur), 'line': C.line(r)}]
for step in range(1, MAXSTEP + 1):
    cands = []
    for g in C.G:
        for k in KEYS:
            if k != cur[g]:
                lay = dict(cur); lay[g] = k
                cands.append((F(C.score(w, lay)) - f, g, k))
    cands.sort()
    if cands[0][0] < -0.3:
        mv = [cands[0][1:]]
    else:
        bp = None
        for (_, g1, k1), (_, g2, k2) in itertools.combinations(cands[:150], 2):
            if g1 != g2:
                lay = dict(cur); lay[g1] = k1; lay[g2] = k2
                d = F(C.score(w, lay)) - f
                if bp is None or d < bp[0]:
                    bp = (d, [(g1, k1), (g2, k2)])
        if bp is None or bp[0] >= -0.6:
            say('无明显改进，结束'); break
        mv = bp[1]
    cur_before = dict(cur)
    for g, k in mv:
        cur[g] = k
    r = C.score(w, cur); f = F(r)
    say(f"步{step} " + ' + '.join(f"{C.NAME[g]} {cur_before[g]}→{k}" for g, k in mv) + f" F={f:.2f} " + C.line(r))
    curve.append({'step': step, 'F': f, 'layout': dict(cur), 'line': C.line(r), 'moves': mv})
    json.dump(curve, open(f'{OUT}.json', 'w', encoding='utf-8'), ensure_ascii=False)
