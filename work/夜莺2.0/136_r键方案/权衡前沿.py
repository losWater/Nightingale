# -*- coding: utf-8 -*-
"""第 5 步：把「搬走的代价」和落点的双拼量对上（2026-09-18）。

第 4 步的意外：当量最好的落点全是 i、u、j、n 这些双拼热门键，而它们的撞词增量也最大。
如果 Δ撞词 与落点的双拼量强正相关，那就等于从反方向证明了论文第二节的因果链——
算法当初把根放在 p，正是因为搬到任何一个双拼热门键都要付避重的账。
"""
import io, sys, os, re, json, math, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
KEYS = 'abcdefghijklmnopqrstuvwxyz'
freq = {}; order = []
for l in open(W + '/30_形码盒子1.0复测/默认字频.txt', encoding='utf-8-sig'):
    p = l.rstrip('\r\n').split('\t')
    if len(p) == 2 and p[1].isdigit(): freq[p[0]] = int(p[1]); order.append(p[0])
irr = json.load(open(W + '/83_单字表重放/无理码表.json', encoding='utf-8-sig'))
IRRALL = {(t, c) for g in ('容错码', '特殊简码', '无理码') for c, t in irr[g].items()}
q = open(W + '/65_群友离线工具包/夜莺2.0离线工具包/拆分查询.html', encoding='utf-8-sig').read()
D = json.JSONDecoder().raw_decode(q[re.search(r'\bconst D\s*=\s*', q).end():])[0]
KEY0 = {}; GRP = {}
for c, d in D.items():
    for r in d.get('根', []): KEY0[r['根']] = r['键']; GRP[r['根']] = r['组']
EQ = {}
for l in open(W + '/54_补删鹿旁保留羊南心四起点试跑/frozen/当量表.tsv', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) >= 2:
        try: EQ[p[0]] = float(p[1])
        except ValueError: pass
eq = lambda a, b: EQ.get(a + b, 1.3)
WORD = set()
for l in open(W + '/00_维护/主表/夜莺2.0字词表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t')
    if len(t) > 1: WORD.add(c)
BASE = []
for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t')
    if len(c) == 4 and len(t) == 1 and (t, c) not in IRRALL and D.get(t, {}).get('根'):
        BASE.append((t, c[:2]))
wf = lambda t: freq.get(t, 0)
TOTF = sum(wf(t) for t, _ in BASE)
# 各键双拼量（全码口径，前两码）
sp = collections.Counter()
for t, s in BASE:
    f = wf(t)
    for ch in s: sp[ch] += f
TSP = sum(sp.values())
SP = {k: sp[k] / TSP * 100 for k in KEYS}

def measure(KEY):
    fm = collections.defaultdict(list)
    amt = collections.Counter(); cost = collections.Counter()
    for t, s in BASE:
        rs = D[t]['根']
        k3, k4 = KEY[rs[0]['根']], KEY[rs[-1]['根']]
        fm[s + k3 + k4].append(t)
        f = wf(t)
        if f:
            amt[k3] += f; cost[k3] += f * eq(s[1], k3)
            amt[k4] += f; cost[k4] += f * eq(k3, k4)
    dup = sum(1 for ts in fm.values() if len(ts) > 1)
    hit = sum(len(ts) for c, ts in fm.items() if c in WORD)
    hitw = sum(wf(t) for c, ts in fm.items() if c in WORD for t in ts)
    return {'重码位': dup, '撞词': hit, '撞词加权': hitw / TOTF * 100,
            '当量': sum(cost.values()) / sum(amt.values())}
B = measure(KEY0)
def corr(xs, ys):
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    d = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / d if d else 0

print('基线　当量 %.4f　重码位 %d　撞词 %d（加权 %.3f%%）' % (B['当量'], B['重码位'], B['撞词'], B['撞词加权']))
ALL = {}
for g in ('横', '儿／子'):
    forms = [x for x in GRP if GRP[x] == g]
    rows = []
    for dst in KEYS:
        if dst == 'p': continue
        K = dict(KEY0)
        for r in forms: K[r] = dst
        m = measure(K)
        rows.append((dst, SP[dst], m['撞词'] - B['撞词'], m['当量'] - B['当量'], m['重码位'] - B['重码位']))
    c = corr([r[1] for r in rows], [r[2] for r in rows])
    c2 = corr([r[1] for r in rows], [r[3] for r in rows])
    ALL[g] = {'相关_双拼量×Δ撞词': round(c, 4), '相关_双拼量×Δ当量': round(c2, 4),
              '逐键': [{'键': d, '双拼量': round(s, 2), 'Δ撞词': w, 'Δ当量': round(e, 5), 'Δ重码位': u}
                      for d, s, w, e, u in rows]}
    print('\n' + '═' * 70)
    print('【%s】搬到各键的代价（按落点双拼量从高到低）' % g)
    print('═' * 70)
    print('  落点  双拼量   Δ撞词   Δ当量    Δ重码位')
    for d, s, w, e, u in sorted(rows, key=lambda x: -x[1]):
        print('   %s   %5.2f%%  %+5d   %+.4f   %+5d' % (d, s, w, e, u))
    print('  ── 落点双拼量 × Δ撞词  相关 %+.3f' % c)
    print('  ── 落点双拼量 × Δ当量  相关 %+.3f' % c2)
json.dump({'基线': B, '各组': ALL}, open(H + '/权衡前沿.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\n→ %s/权衡前沿.json' % H)
