# -*- coding: utf-8 -*-
"""第 4 步：p 上每个组，扫全部 26 个落点，找真正的最优去处（2026-09-18）。

第 3 步发现搬到 r 反而让总当量变差，与论文 3.4「r 是现成的去处」矛盾。
先查原因：r 的「代价量比 0.913」是用 r 现有那批字算的——当量是按键对算的，
换一批字过去，键对分布就变了，r 的便宜未必带得走。
本脚本不预设落点，把 26 个键全试一遍，让数据自己说话。
"""
import io, sys, os, re, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
sys.path.insert(0, H)
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
TOP = set(order[:3500])
wf = lambda t: freq.get(t, 0)
TOTF = sum(wf(t) for t, _ in BASE)

def measure(KEY):
    fm = collections.defaultdict(list); tm = collections.defaultdict(set)
    amt = collections.Counter(); cost = collections.Counter()
    for t, sp in BASE:
        rs = D[t]['根']
        k3, k4 = KEY[rs[0]['根']], KEY[rs[-1]['根']]
        fm[sp + k3 + k4].append(t); tm[sp + k3].add(t)
        f = wf(t)
        if f:
            amt[k3] += f; cost[k3] += f * eq(sp[1], k3)
            amt[k4] += f; cost[k4] += f * eq(k3, k4)
    dup = 0; dcost = 0
    for c, ts in fm.items():
        if len(ts) < 2: continue
        dup += 1
        for i, t in enumerate(sorted(ts, key=lambda x: -wf(x))):
            if i: dcost += wf(t) * i
    t3 = 0; t3c = 0
    for c, ts in tm.items():
        hot = sorted([t for t in ts if t in TOP], key=lambda x: -wf(x))
        if len(hot) < 2: continue
        t3 += 1
        for i, t in enumerate(hot):
            if i: t3c += wf(t) * i
    hit = sum(len(ts) for c, ts in fm.items() if c in WORD)
    tot = sum(amt.values())
    return {'重码位': dup, '选重': dcost / TOTF, '三简挤位': t3, '三简选重': t3c / TOTF,
            '撞词': hit, '当量': sum(cost.values()) / tot,
            '量': {k: amt[k] / tot * 100 for k in KEYS}}

B = measure(KEY0)
print('基线　当量 %.4f　重码位 %d　选重 %.4f　三简挤位 %d　三简选重 %.4f　撞词 %d'
      % (B['当量'], B['重码位'], B['选重'], B['三简挤位'], B['三简选重'], B['撞词']))

# ── 先解释 r 为什么没带走便宜 ──
print('\n' + '═' * 76)
print('查因：当量是按「键对」算的，不是按键算的')
print('═' * 76)
pref = collections.Counter(); rref = collections.Counter()
for t, sp in BASE:
    rs = D[t]['根']; f = wf(t)
    if not f: continue
    k3 = KEY0[rs[0]['根']]
    if k3 == 'p': pref[sp[1]] += f
    if k3 == 'r': rref[sp[1]] += f
print('  进入 p 做首根时，前一码（双拼第二码）是谁——以及那一跳的当量：')
for k, v in pref.most_common(6):
    print('    %s→p  占 %5.1f%%   当量 %.3f' % (k, v / sum(pref.values()) * 100, eq(k, 'p')))
print('  进入 r 做首根时：')
for k, v in rref.most_common(6):
    print('    %s→r  占 %5.1f%%   当量 %.3f' % (k, v / sum(rref.values()) * 100, eq(k, 'r')))
print('  p 的加权入键当量 %.4f   r 的加权入键当量 %.4f'
      % (sum(v * eq(k, 'p') for k, v in pref.items()) / sum(pref.values()),
         sum(v * eq(k, 'r') for k, v in rref.items()) / sum(rref.values())))
print('  但若把 p 这批字原样搬到 r，入键当量会变成 %.4f'
      % (sum(v * eq(k, 'r') for k, v in pref.items()) / sum(pref.values())))

# ── 26 落点全扫 ──
pg = collections.Counter()
for t, sp in BASE:
    rs = D[t]['根']; f = wf(t)
    if not f: continue
    for r in (rs[0]['根'], rs[-1]['根']):
        if KEY0[r] == 'p': pg[GRP[r]] += f
print('\n' + '═' * 76)
print('26 个落点全扫：每组搬到哪个键最划算')
print('═' * 76)
RES = {}
for g, v in pg.most_common(6):
    forms = [x for x in GRP if GRP[x] == g]
    rows = []
    for dst in KEYS:
        if dst == 'p': continue
        K = dict(KEY0)
        for r in forms: K[r] = dst
        m = measure(K)
        rows.append((dst, m))
    rows.sort(key=lambda x: x[1]['当量'])
    RES[g] = [{'键': d, '当量': m['当量'], '重码位': m['重码位'], '选重': m['选重'],
               '撞词': m['撞词'], 'p量': m['量']['p'], '落点量': m['量'][d]} for d, m in rows]
    print('\n【%s】占 p 的 %.1f%%' % (g, v / sum(pg.values()) * 100))
    print('  落点  当量      Δ当量     重码位   Δ重码  撞词   Δ撞词   p字根量  落点字根量')
    for d, m in rows[:5]:
        print('   %s   %.4f  %+.4f   %5d  %+5d  %5d  %+5d   %5.2f%%   %5.2f%%'
              % (d, m['当量'], m['当量'] - B['当量'], m['重码位'], m['重码位'] - B['重码位'],
                 m['撞词'], m['撞词'] - B['撞词'], m['量']['p'], m['量'][d]))
    ri = [i for i, (d, _) in enumerate(rows) if d == 'r'][0]
    rm = rows[ri][1]
    print('   …   r 排第 %d：当量 %.4f (%+.4f)  重码位 %+d  撞词 %+d'
          % (ri + 1, rm['当量'], rm['当量'] - B['当量'], rm['重码位'] - B['重码位'], rm['撞词'] - B['撞词']))
json.dump({'基线': {k: v for k, v in B.items() if k != '量'}, '落点': RES},
          open(H + '/落点扫描.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s/落点扫描.json' % H)
