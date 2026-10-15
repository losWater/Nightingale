"""第二轮精修（2026-10-13，大佬建议）：形码部分（扣掉双拼 1→2）的大跨排、小指干扰不输夜莺3.1，再在三码、全码重上找补。
形码部分手感：前1521 读音（排除固定一二简），全码 2→3、3→4 两段，测评站口径（大跨排=形码盒子 ms；小指干扰=同手小指键与无名指键连按），按读音个数计。
F = 1000×门禁 + 500×形码成本 + 5×(大跨−夜莺)⁺ + 5×(小指−夜莺)⁺ + 0.3×(大跨+小指)
    + 0.5×前1500非独占 + 0.1×前3500非独占 − 0.05×三简 + 2×(四码−120)⁺ + 2×前3571选重 + 1667×(p−0.04)⁺
用法：../../.venv/bin/python polish2.py <起点 json> <起点步> <最多步数> <输出名>"""
import itertools, json, sys
import yaml
import common as C
KEYS = 'abcdefghijklmnopqrstuvwxyz'
Mc = json.load(open(C.ROOT / 'eval/box/combo.json'))
fin = {}
for row in ('qwert', 'asdfg', 'zxcvb'):
    for i, k in enumerate(row): fin[k] = ('L', [0, 1, 2, 3, 3][i])
for row in ('yuiop', 'hjkl;', 'nm,./'):
    for i, k in enumerate(row): fin[k] = ('R', [3, 3, 2, 1, 0][i])
MS = {a + b: bool(Mc[a + b]['ms']) for a in KEYS for b in KEYS}
PD = {a + b: fin[a][0] == fin[b][0] and {fin[a][1], fin[b][1]} == {0, 1} for a in KEYS for b in KEYS}
Ev = yaml.load(open(C.E.INP / 'elements.yaml', encoding='utf-8'), Loader=yaml.CSafeLoader)
T1 = set(C.E.META['tier_indices']['1500'])
RD = [(e['元素序列'][1]['element'][2:], e['元素序列'][2]['element'], e['元素序列'][3]['element'])
      for i, e in enumerate(Ev) if i in T1 and not e.get('简码长度')]


def feel(lay):
    ms = pd = 0
    for k2, g3, g4 in RD:
        a, b = k2 + lay[g3], lay[g3] + lay[g4]
        ms += MS[a] + MS[b]; pd += PD[a] + PD[b]
    return ms, pd


def evaluate(w, lay):
    r = C.score(w, lay); r['ms'], r['pd'] = feel(lay); return r


# 夜莺3.1 基准：小鹤音码 + NB46（同一套读音、拆分），只是第 2 码换回小鹤
sys.path.insert(0, str(C.ROOT / 'lib'))
from shuangpin import encode
xh2 = [encode(e['拼音'], 'xiaohe')[1] for i, e in enumerate(Ev) if i in T1 and not e.get('简码长度')]
def feel_xh(lay):
    ms = pd = 0
    for (k2, g3, g4), x in zip(RD, xh2):
        a, b = x + lay[g3], lay[g3] + lay[g4]
        ms += MS[a] + MS[b]; pd += PD[a] + PD[b]
    return ms, pd
MS0, PD0 = feel_xh(C.B)


def F(r):
    return (1000 * r['pen'] + 500 * r['cost'] + 5 * max(0, r['ms'] - MS0) + 5 * max(0, r['pd'] - PD0) + 0.3 * (r['ms'] + r['pd'])
            + 0.5 * r['excl'][0] + 0.1 * r['excl'][1] - 0.05 * r['san'] + 2 * max(0, r['four_top'] - 120)
            + 2 * r['excl'][3] + 1667 * max(0, r['p_share'] - 0.04))


def line(r):
    return C.line(r) + f" 非独占{r['excl'][:2]} 形部大跨{r['ms']} 形部小指{r['pd']}"


if __name__ == '__main__':
    src, st, MAXSTEP, OUT = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    cur = dict({c['step']: c for c in json.load(open(src, encoding='utf-8'))}[st]['layout'])
    w = C.Worker(); r = evaluate(w, cur); f = F(r)
    log = open(f'{OUT}.log', 'w')
    def say(*a):
        print(*a, flush=True); print(*a, file=log, flush=True)
    say(f'夜莺3.1 形部基准：大跨{MS0} 小指{PD0}')
    say('起点', f'F={f:.2f}', line(r))
    curve = [{'step': 0, 'F': f, 'layout': dict(cur), 'line': line(r)}]
    for step in range(1, MAXSTEP + 1):
        cands = []
        for g in C.G:
            for k in KEYS:
                if k != cur[g]:
                    lay = dict(cur); lay[g] = k
                    cands.append((F(evaluate(w, lay)) - f, g, k))
        cands.sort()
        if cands[0][0] < -0.3:
            mv = [cands[0][1:]]
        else:
            bp = None
            for (_, g1, k1), (_, g2, k2) in itertools.combinations(cands[:150], 2):
                if g1 != g2:
                    lay = dict(cur); lay[g1] = k1; lay[g2] = k2
                    d = F(evaluate(w, lay)) - f
                    if bp is None or d < bp[0]:
                        bp = (d, [(g1, k1), (g2, k2)])
            if bp is None or bp[0] >= -0.6:
                say('无明显改进，结束'); break
            mv = bp[1]
        before = dict(cur)
        for g, k in mv:
            cur[g] = k
        r = evaluate(w, cur); f = F(r)
        say(f"步{step} " + ' + '.join(f"{C.NAME[g]} {before[g]}→{k}" for g, k in mv) + f" F={f:.2f} " + line(r))
        curve.append({'step': step, 'F': f, 'layout': dict(cur), 'line': line(r), 'moves': mv})
        json.dump(curve, open(f'{OUT}.json', 'w', encoding='utf-8'), ensure_ascii=False)
