# -*- coding: utf-8 -*-
"""验证「避重把高频根推向双拼冷门键」这个推论（2026-09-17 群主提出）。

推论链：
  ① 退火的目标里有字词避重，办法是让字根绕开高频的双拼按键组合；
  ② p 只有 ie 一个音，双拼层几乎不用，全码 abxp 这种组合天然不容易与词撞；
  ③ 于是算法倾向于把高频根往 p 这类冷门音键上堆，尤其是末根位；
  ④ 字的全码末根本来就容易拆到笔画，所以 p 天然吸笔画根——1.0 是撇，2.0 是横。

三项检验：
  A 双拼量与字根量是否负相关（键级相关系数）
  B 首根位与末根位分开统计，看 p 是不是末根大户
  C 笔画根都落在哪些键，那些键的双拼量如何
"""
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
full = {}
for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t')
    if (t, c) in skip: continue
    codes[t].append(c)
    if len(c) == 4 and t not in full: full[t] = c
best = {t: min(cs, key=lambda c: (len(c), cs.index(c))) for t, cs in codes.items()}
q = open(W + '/65_群友离线工具包/夜莺2.0离线工具包/拆分查询.html', encoding='utf-8-sig').read()
D = json.JSONDecoder().raw_decode(q[re.search(r'\bconst D\s*=\s*', q).end():])[0]
KEY = {}; GROUP = {}
for c, d in D.items():
    for r in d.get('根', []): KEY[r['根']] = r['键']; GROUP[r['根']] = r['组']
KEYS = 'abcdefghijklmnopqrstuvwxyz'
N = 1500
sp = collections.Counter(); first = collections.Counter(); last = collections.Counter()
froot = collections.defaultdict(collections.Counter); lroot = collections.defaultdict(collections.Counter)
for t, f in freq[:N]:
    c = best.get(t)
    if not c: continue
    for ch in c[:2]: sp[ch] += f                        # 双拼那两码（按实际打出来的长度截断）
    if len(c) < 3: continue
    rs = D.get(t, {}).get('根')
    if not rs: continue
    first[c[2]] += f; froot[c[2]][rs[0]['根']] += f
    if len(c) == 4: last[c[3]] += f; lroot[c[3]][rs[-1]['根']] += f
def norm(cnt):
    s = sum(cnt.values()); return {k: cnt.get(k, 0) / s * 100 for k in KEYS}
S, F, L = norm(sp), norm(first), norm(last)
R = {k: (first.get(k, 0) + last.get(k, 0)) for k in KEYS}; rs_ = sum(R.values()); R = {k: v / rs_ * 100 for k, v in R.items()}
def corr(a, b):
    xs = [a[k] for k in KEYS]; ys = [b[k] for k in KEYS]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return cov / math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
print('══════ A 双拼量 vs 字根量（前 %d 字，键级）══════' % N)
print('  双拼量 与 字根总量 的相关系数：%+.3f' % corr(S, R))
print('  双拼量 与 首根量   的相关系数：%+.3f' % corr(S, F))
print('  双拼量 与 末根量   的相关系数：%+.3f  ← 推论③ 说这里应当是明显的负相关' % corr(S, L))
print('\n键  双拼量   首根量   末根量   字根总量   （按双拼量升序，最冷门的音在最上面）')
for k in sorted(KEYS, key=lambda x: S[x]):
    print('  %s  %5.2f%%  %5.2f%%  %5.2f%%   %5.2f%%' % (k, S[k], F[k], L[k], R[k]))
print('\n══════ B 首根位 vs 末根位 ══════')
print('键  末根量占该键字根量的比例（越高＝越是末根大户）')
for k in sorted(KEYS, key=lambda x: -(last.get(x, 0) / max(1, first.get(x, 0) + last.get(x, 0)))):
    tot = first.get(k, 0) + last.get(k, 0)
    if not tot: continue
    print('  %s  %5.1f%%   （双拼量 %5.2f%%，字根量 %5.2f%%）' % (k, last.get(k, 0) / tot * 100, S[k], R[k]))
print('\n══════ C 笔画根都在哪些键 ══════')
STROKE = ['横', '竖', '撇', '点', '折', '一', '二', '丨', '丶', '丿', '乂', '八', '十', '乛']
rows = []
for r in sorted(KEY, key=lambda x: -(froot_sum := sum(froot[KEY[x]].get(x, 0) for _ in [0]) + lroot[KEY[x]].get(x, 0))):
    if r in STROKE or (len(r) == 1 and r in '一丨丿丶乛乂二三亅'):
        k = KEY[r]; fv = froot[k].get(r, 0); lv = lroot[k].get(r, 0)
        rows.append((r, k, fv, lv, S[k]))
tot_root = first.total() + last.total() if hasattr(first, 'total') else sum(first.values()) + sum(last.values())
print('根    键   首根量    末根量    末根占比   该键双拼量')
for r, k, fv, lv, s in sorted(rows, key=lambda x: -(x[2] + x[3])):
    if fv + lv == 0: continue
    print('%-4s  %s   %5.2f%%   %5.2f%%   %5.0f%%     %5.2f%%' % (r, k, fv / tot_root * 100, lv / tot_root * 100, lv / (fv + lv) * 100, s))
json.dump({'双拼量': S, '首根量': F, '末根量': L, '字根总量': R,
           '相关系数': {'双拼×字根总量': round(corr(S, R), 4), '双拼×首根': round(corr(S, F), 4), '双拼×末根': round(corr(S, L), 4)},
           '各键末根占比': {k: round(last.get(k, 0) / max(1, first.get(k, 0) + last.get(k, 0)) * 100, 2) for k in KEYS}},
          open(H + '/避重推论验证.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s/避重推论验证.json' % H)
