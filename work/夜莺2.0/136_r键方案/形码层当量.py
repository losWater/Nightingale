# -*- coding: utf-8 -*-
"""形码层当量：把第 3、4 码单独立成一个指标（2026-09-18，用户提议）。

三条键对，分属三层：
  双拼层   第1码 → 第2码    完全由小鹤双拼决定，形码动不了，只作背景
  跨层     第2码 → 第3码    即「音末到首形」，已知计权 0.25
  形码层   第3码 → 第4码    即「全码形到形」，清单措辞是「也核对」，是否计权待查

决定性检验（不用翻 yaml）：
  零假设 = 把 26 个键的标签随机重排。字根分组、谁跟谁共键、双拼码全部不动，
  只换每一桶根落在哪个物理键上。在这个零分布里看现行布局排第几个百分位。
  · 若某项进过目标函数 → 现行布局应显著优于随机（低百分位）
  · 若某项只报告不计分 → 现行布局应落在随机分布中间（约 50 百分位）
  「音末到首形」已知计权 0.25，是阳性对照。两项一比，答案自明。
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
SKIP = {(t, c) for g in ('容错码', '特殊简码') for c, t in irr[g].items()}
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
codes = collections.defaultdict(list); full = {}
for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t')
    if (t, c) in SKIP: continue
    codes[t].append(c)
    if len(c) == 4 and len(t) == 1 and (t, c) not in IRRALL and t not in full: full[t] = c
best = {t: min(cs, key=lambda c: (len(c), cs.index(c))) for t, cs in codes.items()}
# 样本：有全码且有拆分的字
SAMP = [(t, full[t][:2], D[t]['根']) for t in order if t in full and D.get(t, {}).get('根') and freq.get(t)]
print('样本 %d 字（有全码、有拆分、有字频）' % len(SAMP))

def layers(KEY, sub):
    """返回三层的加权平均当量"""
    a = b = c = 0.0; w = 0.0
    for t, sp, rs in sub:
        f = freq[t]; w += f
        k3, k4 = KEY[rs[0]['根']], KEY[rs[-1]['根']]
        a += f * eq(sp[0], sp[1])       # 双拼层
        b += f * eq(sp[1], k3)          # 跨层：音末到首形
        c += f * eq(k3, k4)             # 形码层：形到形
    return a / w, b / w, c / w

BANDS = [('前 500', 500), ('前 1500', 1500), ('前 3500', 3500), ('全部', len(SAMP))]
print('\n' + '═' * 72)
print('一、三层当量各是多少（全码口径）')
print('═' * 72)
print('  档位      双拼层    跨层(音末→首形)   形码层(形→形)')
LAY = {}
for name, n in BANDS:
    sub = [x for x in SAMP[:n]]
    a, b, c = layers(KEY0, sub)
    LAY[name] = {'双拼层': a, '跨层': b, '形码层': c}
    print('  %-8s  %.4f      %.4f           %.4f' % (name, a, b, c))
print('\n  注：当量越小越省力。双拼层由小鹤固定，形码怎么排都动不了它。')

# ── 决定性检验：与随机键标重排比 ──
print('\n' + '═' * 72)
print('二、决定性检验：现行布局 vs 随机重排 26 个键标')
print('═' * 72)
print('  零假设保持分组与共键结构不变，只随机换每桶根落在哪个物理键上。')
N = 3000
random.seed(20260918)
for name, n in (('前 1500', 1500), ('前 3500', 3500)):
    sub = SAMP[:n]
    a0, b0, c0 = layers(KEY0, sub)
    bs = []; cs = []
    for _ in range(N):
        perm = list(KEYS); random.shuffle(perm)
        m = dict(zip(KEYS, perm))
        K = {r: m[k] for r, k in KEY0.items()}
        _, b, c = layers(K, sub)
        bs.append(b); cs.append(c)
    pb = sum(1 for x in bs if x <= b0) / N * 100
    pc = sum(1 for x in cs if x <= c0) / N * 100
    mb, mc = sum(bs) / N, sum(cs) / N
    print('\n  【%s】%d 次随机重排' % (name, N))
    print('    跨层  音末→首形   现行 %.4f   随机均值 %.4f   百分位 %5.1f%%   %s'
          % (b0, mb, pb, '← 显著优于随机' if pb < 10 else ('← 与随机无异' if 30 < pb < 70 else '← 略优于随机')))
    print('    形码层 形→形     现行 %.4f   随机均值 %.4f   百分位 %5.1f%%   %s'
          % (c0, mc, pc, '← 显著优于随机' if pc < 10 else ('← 与随机无异' if 30 < pc < 70 else '← 略优于随机')))
    LAY.setdefault('检验', {})[name] = {'跨层现行': b0, '跨层随机均值': mb, '跨层百分位': pb,
                                       '形码层现行': c0, '形码层随机均值': mc, '形码层百分位': pc}

# ── 各键在形码层的贡献 ──
print('\n' + '═' * 72)
print('三、形码层：各键作为末根键时，进入它那一跳有多贵（前 1500）')
print('═' * 72)
amt = collections.Counter(); cost = collections.Counter()
for t, sp, rs in SAMP[:1500]:
    f = freq[t]; k3, k4 = KEY0[rs[0]['根']], KEY0[rs[-1]['根']]
    amt[k4] += f; cost[k4] += f * eq(k3, k4)
rows = [(k, amt[k], cost[k] / amt[k]) for k in KEYS if amt[k]]
ta = sum(amt.values())
print('  键   末根量    平均当量   （按平均当量降序，最贵的在上面）')
for k, a, e in sorted(rows, key=lambda x: -x[2]):
    print('   %s   %5.2f%%    %.4f%s' % (k, a / ta * 100, e, '   ← p' if k == 'p' else ''))
json.dump(LAY, open(H + '/形码层当量.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s/形码层当量.json' % H)
