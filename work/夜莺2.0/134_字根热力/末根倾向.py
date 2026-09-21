# -*- coding: utf-8 -*-
"""末根倾向（2026-09-17 你指出：1.0 的 p 上有辶、卩，也是高频根，而且它们往往是末根）。

定义：某个根的「末根倾向」＝ 它作为末根被敲的量 ÷（作为首根 + 作为末根）。
  辶、卩、阝 这类在书写顺序里必然靠后的根，倾向应接近 1；
  亻、氵、扌 这类偏旁必然靠前，倾向应接近 0。
检验：p 键上的根，末根倾向是不是显著高于别的键——如果是，那两代 p 的共性就不是「笔画根」，
而是「末根大户」，与「p 承担大量末根使用点」的推理完全对上。
顺带查 1.0 的 p 键那批根（母、辶、鬼、变字头、卩、田、十、力、古、束、丘、耂）在 2.0 的去向与倾向。"""
import io, sys, os, re, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
freq = []
for l in open(W + '/30_形码盒子1.0复测/默认字频.txt', encoding='utf-8-sig'):
    p = l.rstrip('\r\n').split('\t')
    if len(p) == 2 and p[1].isdigit(): freq.append((p[0], int(p[1])))
irr = json.load(open(W + '/83_单字表重放/无理码表.json', encoding='utf-8-sig'))
skip = {(t, c) for grp in ('容错码', '特殊简码') for c, t in irr[grp].items()}
codes = collections.defaultdict(list); full = {}
for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t')
    if (t, c) in skip: continue
    codes[t].append(c)
    if len(c) == 4 and t not in full: full[t] = c
q = open(W + '/65_群友离线工具包/夜莺2.0离线工具包/拆分查询.html', encoding='utf-8-sig').read()
D = json.JSONDecoder().raw_decode(q[re.search(r'\bconst D\s*=\s*', q).end():])[0]
KEY = {}
for c, d in D.items():
    for r in d.get('根', []): KEY[r['根']] = r['键']
# 用全码口径统计首末：每个字的全码都用到首末两根，样本最全
F = collections.Counter(); L = collections.Counter()
for t, f in freq[:3500]:
    rs = D.get(t, {}).get('根')
    if not rs or t not in full: continue
    F[rs[0]['根']] += f; L[rs[-1]['根']] += f
tend = {r: L[r] / (F[r] + L[r]) for r in set(F) | set(L) if F[r] + L[r] > 0}
amt = {r: F[r] + L[r] for r in tend}
tot = sum(amt.values())
print('══════ 各键上的根：加权平均末根倾向 ══════')
print('（1.0 ＝ 只当末根，0.0 ＝ 只当首根。按倾向降序）')
bykey = collections.defaultdict(list)
for r, v in amt.items():
    if r in KEY: bykey[KEY[r]].append(r)
rows = []
for k, rs in bykey.items():
    w = sum(amt[r] for r in rs)
    if not w: continue
    t = sum(tend[r] * amt[r] for r in rs) / w
    rows.append((k, t, w / tot * 100, len(rs)))
for k, t, w, n in sorted(rows, key=lambda x: -x[1]):
    mark = '  ← p' if k == 'p' else ''
    print('  %s   %.3f   字根量 %5.2f%%   %2d 个根%s' % (k, t, w, n, mark))
print('\n══════ p 键上的根，各自的末根倾向 ══════')
ps = sorted([r for r in bykey.get('p', [])], key=lambda r: -amt[r])
print('根      末根倾向   占全局字根量')
for r in ps[:16]:
    print('  %-6s %.3f      %5.2f%%' % (r, tend[r], amt[r] / tot * 100))
print('\n══════ 1.0 的 p 键那批根，在 2.0 的去向 ══════')
OLD = ['母', '辶', '鬼', '变字头', '卩', '田', '十', '力', '古', '束', '丘', '耂']
print('根      2.0 的键   末根倾向   占全局字根量')
for r in OLD:
    k = KEY.get(r, '（2.0 无此根形）')
    if r in tend: print('  %-6s %-8s  %.3f      %5.2f%%' % (r, k, tend[r], amt[r] / tot * 100))
    else: print('  %-6s %-8s  —' % (r, k))
print('\n══════ 全局末根倾向最高的根（量 > 0.3%）══════')
hi = sorted([r for r in tend if amt[r] / tot * 100 > 0.3], key=lambda r: -tend[r])[:22]
print('根      键   末根倾向   占全局字根量')
for r in hi: print('  %-6s %s    %.3f      %5.2f%%' % (r, KEY.get(r, '?'), tend[r], amt[r] / tot * 100))
json.dump({'各键平均末根倾向': {k: round(t, 4) for k, t, _, _ in rows},
           'p键各根': [{'根': r, '末根倾向': round(tend[r], 4), '占全局%': round(amt[r] / tot * 100, 3)} for r in ps],
           '1.0的p键去向': [{'根': r, '2.0的键': KEY.get(r, ''), '末根倾向': round(tend.get(r, -1), 4), '占全局%': round(amt.get(r, 0) / tot * 100, 3)} for r in OLD]},
          open(H + '/末根倾向.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s/末根倾向.json' % H)
