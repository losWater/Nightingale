# -*- coding: utf-8 -*-
"""决定性检验第二步：在键标重排的零分布里，看现行布局在各项上各排第几（2026-09-18）。

关键性质：随机重排 26 个键标，不改变任何单字重码——谁跟谁共键完全没动，
所以全部 26! 种重排在「单字重码」这一项上严格等价。
变的只有两项：键对当量、字词碰撞。
那么现行布局在这两项上的百分位，就直接告诉我们当初是哪一项在主导选择。
"""
import io, sys, os, re, json, random, collections
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
KEY0 = {}
for c, d in D.items():
    for r in d.get('根', []): KEY0[r['根']] = r['键']
EQ = {}
for l in open(W + '/54_补删鹿旁保留羊南心四起点试跑/frozen/当量表.tsv', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) >= 2:
        try: EQ[p[0]] = float(p[1])
        except ValueError: pass
eq = lambda a, b: EQ.get(a + b, 1.3)
WFREQ = {}
for l in open(W + '/08_词库与词频重建/二字词60000_自动分流.jsonl', encoding='utf-8'):
    try: d = json.loads(l)
    except Exception: continue
    s = d.get('各源原始词频') or {}
    v = s.get('bcc_balanced') or (max(s.values()) if s else 0)
    if v: WFREQ[d['词']] = float(v)
WORD = collections.defaultdict(list)
for l in open(W + '/00_维护/主表/夜莺2.0字词表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t')
    if len(t) > 1: WORD[c].append(t)
full = {}
for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t')
    if len(c) == 4 and len(t) == 1 and (t, c) not in IRRALL and t not in full: full[t] = c
SAMP = [(t, full[t][:2], D[t]['根']) for t in order if t in full and D.get(t, {}).get('根') and freq.get(t)]
ALL = [(t, full[t][:2], D[t]['根']) for t in full if D.get(t, {}).get('根')]
print('当量样本 %d 字，撞词样本 %d 字' % (len(SAMP), len(ALL)))

def metrics(KEY):
    # 当量：跨层与形码层（前 3500 加权）
    b = c = w = 0.0
    for t, sp, rs in SAMP[:3500]:
        f = freq[t]; w += f
        k3, k4 = KEY[rs[0]['根']], KEY[rs[-1]['根']]
        b += f * eq(sp[1], k3); c += f * eq(k3, k4)
    # 撞词：全表口径，计数与词频量
    n = 0; wm = 0.0
    for t, sp, rs in ALL:
        code = sp + KEY[rs[0]['根']] + KEY[rs[-1]['根']]
        ws = WORD.get(code)
        if ws:
            n += 1
            for x in ws: wm += WFREQ.get(x, 0)
    return b / w, c / w, n, wm

b0, c0, n0, w0 = metrics(KEY0)
print('\n现行布局：跨层当量 %.4f   形码层当量 %.4f   撞词 %d 处   撞词词频量 %.4g' % (b0, c0, n0, w0))
N = 600
random.seed(20260918)
B = []; C = []; NN = []; WW = []
for i in range(N):
    perm = list(KEYS); random.shuffle(perm)
    m = dict(zip(KEYS, perm))
    K = {r: m[k] for r, k in KEY0.items()}
    b, c, n, wm = metrics(K)
    B.append(b); C.append(c); NN.append(n); WW.append(wm)
def pct(v, arr): return sum(1 for x in arr if x <= v) / len(arr) * 100
print('\n' + '═' * 76)
print('在 %d 次随机键标重排中，现行布局排第几个百分位（越低越好）' % N)
print('═' * 76)
print('  注：这些重排的单字重码完全相同，所以只有下面两类指标在变。\n')
rows = [('跨层当量 音末→首形', b0, B), ('形码层当量 形→形', c0, C),
        ('字词碰撞 按码位计数', n0, NN), ('字词碰撞 按词频加权', w0, WW)]
for name, v, arr in rows:
    p = pct(v, arr); mn, mx = min(arr), max(arr); mean = sum(arr) / len(arr)
    tag = '★ 显著优于随机' if p < 5 else ('优于随机' if p < 25 else ('与随机无异' if p < 75 else '劣于随机'))
    print('  %-20s 现行 %12.4f   随机 %.4f～%.4f（均值 %.4f）   百分位 %5.1f%%   %s'
          % (name, v, mn, mx, mean, p, tag))
print('\n解读：所有重排在单字重码上等价。若某项百分位很低，说明当初的选择由它主导；')
print('      若某项落在中间，说明它没有参与选择。')
json.dump({'现行': {'跨层当量': b0, '形码层当量': c0, '撞词计数': n0, '撞词词频量': w0},
           '百分位': {name: pct(v, arr) for name, v, arr in rows},
           '随机均值': {name: sum(arr) / len(arr) for name, v, arr in rows}},
          open(H + '/谁主导了布局.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s/谁主导了布局.json' % H)
