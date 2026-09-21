# -*- coding: utf-8 -*-
"""写论文前补两组论据：
  A 键位当量（手感）与字根量的关系——难按的键是不是反而扛着更多字根；
  B 1.0 与 2.0 的 p 键内容对照——两代都吸笔画根，说明不是偶然；
  C 假如把字根层负担单列进目标函数，现状离"理想"有多远（给个可量化的缺口）。"""
import io, sys, os, re, json, math, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
freq = []
for l in open(W + '/30_形码盒子1.0复测/默认字频.txt', encoding='utf-8-sig'):
    p = l.rstrip('\r\n').split('\t')
    if len(p) == 2 and p[1].isdigit(): freq.append((p[0], int(p[1])))
irr = json.load(open(W + '/83_单字表重放/无理码表.json', encoding='utf-8-sig'))
skip = {(t, c) for grp in ('容错码', '特殊简码') for c, t in irr[grp].items()}
codes = collections.defaultdict(list)
for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t')
    if (t, c) not in skip: codes[t].append(c)
best = {t: min(cs, key=lambda c: (len(c), cs.index(c))) for t, cs in codes.items()}
q = open(W + '/65_群友离线工具包/夜莺2.0离线工具包/拆分查询.html', encoding='utf-8-sig').read()
D = json.JSONDecoder().raw_decode(q[re.search(r'\bconst D\s*=\s*', q).end():])[0]
KEY = {}; GROUP = {}
for c, d in D.items():
    for r in d.get('根', []): KEY[r['根']] = r['键']; GROUP[r['根']] = r['组']
EQ = {}
for l in open(W + '/54_补删鹿旁保留羊南心四起点试跑/frozen/当量表.tsv', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) >= 2:
        try: EQ[p[0]] = float(p[1])
        except ValueError: pass
KEYS = 'abcdefghijklmnopqrstuvwxyz'
def corr(xs, ys):
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
# 键的"固有难度"：该键与其他所有键组合的平均当量（近似手感成本）
hard = {k: sum(EQ.get(a + k, 1.3) for a in KEYS) / 26 for k in KEYS}
sp = collections.Counter(); root = collections.Counter(); first = collections.Counter(); last = collections.Counter()
for t, f in freq[:1500]:
    c = best.get(t)
    if not c: continue
    for ch in c[:2]: sp[ch] += f
    if len(c) < 3: continue
    rs = D.get(t, {}).get('根')
    if not rs: continue
    first[c[2]] += f; root[c[2]] += f
    if len(c) == 4: last[c[3]] += f; root[c[3]] += f
n = lambda d: {k: d.get(k, 0) / sum(d.values()) * 100 for k in KEYS}
S, R, F, L = n(sp), n(root), n(first), n(last)
print('══════ A 键的固有难度 vs 各项用量（前 1500）══════')
print('  难度 × 双拼量   %+.3f' % corr([hard[k] for k in KEYS], [S[k] for k in KEYS]))
print('  难度 × 字根量   %+.3f   ← 若为正，说明难按的键反而扛更多字根' % corr([hard[k] for k in KEYS], [R[k] for k in KEYS]))
print('  难度 × 末根量   %+.3f' % corr([hard[k] for k in KEYS], [L[k] for k in KEYS]))
print('\n  键  固有难度  双拼量  字根量   （按固有难度降序，最难按的在最上面）')
for k in sorted(KEYS, key=lambda x: -hard[x]):
    print('   %s   %.4f   %5.2f%%  %5.2f%%' % (k, hard[k], S[k], R[k]))
# B 1.0 与 2.0 的 p 键
print('\n\n══════ B 两代 p 键上的根 ══════')
cur = sorted({r for r, k in KEY.items() if k == 'p'})
print('  2.0 的 p 键（%d 个根形）：%s' % (len(cur), '、'.join(cur)))
old = None
for cand in (W + '/../releases/v1.0/03_字根与拆分', 'D:/nightingale/releases/v1.0/03_字根与拆分'):
    if os.path.isdir(cand):
        for fn in os.listdir(cand):
            if '键位' in fn or '字根表' in fn:
                txt = open(cand + '/' + fn, encoding='utf-8-sig', errors='replace').read()
                for line in txt.splitlines():
                    if line.strip().lower().startswith('p') and len(line) > 3: old = line.strip(); break
        break
print('  1.0 的 p 键：%s' % (old or '（未在 releases/v1.0 里定位到键位表，正文里按你说的「1.0 是撇、2.0 是横」写）'))
# C 缺口：现状 vs 把字根量按难度重排的理想
ideal = sorted(KEYS, key=lambda k: hard[k])                      # 最好按的在前
actual = sorted(KEYS, key=lambda k: -R[k])                        # 字根量最大的在前
cost_now = sum(R[k] * hard[k] for k in KEYS)
cost_best = sum(sorted([R[k] for k in KEYS], reverse=True)[i] * sorted([hard[k] for k in KEYS])[i] for i in range(26))
print('\n\n══════ C 缺口：字根量若按键的固有难度重排 ══════')
print('  现状加权成本  %.4f' % cost_now)
print('  理想加权成本  %.4f  （量最大的根配最好按的键，仅作下界参考）' % cost_best)
print('  缺口 %.2f%%' % ((cost_now - cost_best) / cost_best * 100))
print('  字根量最大的前 6 个键：%s' % '  '.join('%s(难度%.3f)' % (k, hard[k]) for k in actual[:6]))
print('  最好按的前 6 个键：    %s' % '  '.join('%s(字根量%.2f%%)' % (k, R[k]) for k in ideal[:6]))
json.dump({'固有难度': hard, '双拼量': S, '字根量': R, '首根量': F, '末根量': L,
           '相关': {'难度×双拼': round(corr([hard[k] for k in KEYS], [S[k] for k in KEYS]), 4),
                   '难度×字根': round(corr([hard[k] for k in KEYS], [R[k] for k in KEYS]), 4),
                   '难度×末根': round(corr([hard[k] for k in KEYS], [L[k] for k in KEYS]), 4)},
           '现状成本': round(cost_now, 4), '下界成本': round(cost_best, 4), '缺口%': round((cost_now - cost_best) / cost_best * 100, 2),
           '2.0的p键根形': cur},
          open(H + '/补充论据.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s/补充论据.json' % H)
