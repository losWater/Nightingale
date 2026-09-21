# -*- coding: utf-8 -*-
"""每个键只看它使用量最高的前 30% / 50% 根（2026-09-17 你提的口径）。

用意：一个键的量，是头部几个根撑起来的，还是一堆长尾根堆出来的？
  · 若取前 30% 后排名不掉，说明核心负担就在头部几个根上——这个键是真忙。
  · 若取前 30% 后排名大跌，说明它的量是长尾凑的——单个根都不重。
根数按四舍五入取（至少 1 个）。另附三个口径的排名对照与落差。"""
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
BANDS = [('前 500', 500), ('前 1500', 1500), ('前 3500', 3500)]
PCTS = [('全部', 1.0), ('前 50%', 0.5), ('前 30%', 0.3)]
ALL = {}
for name, n in BANDS:
    bykey = collections.defaultdict(collections.Counter); shape = collections.Counter(); keys = collections.Counter()
    for t, f in freq[:n]:
        c = best.get(t)
        if not c: continue
        for ch in c: keys[ch] += f
        if len(c) < 3: continue
        rs = D.get(t, {}).get('根')
        if not rs: continue
        for r in [rs[0]['根']] + ([rs[-1]['根']] if len(c) == 4 else []):
            shape[r] += f; bykey[KEY[r]][r] += f
    srank = {r: i for i, (r, _) in enumerate(shape.most_common(), 1)}
    krank = {k: i for i, (k, _) in enumerate(keys.most_common(), 1)}
    cut = {}
    for label, p in PCTS:
        amt = {}
        for k, cnt in bykey.items():
            top = cnt.most_common(); m = max(1, int(round(len(top) * p)))
            amt[k] = (sum(v for _, v in top[:m]), m, [r for r, _ in top[:m]])
        tot = sum(v for v, _, _ in amt.values())
        rank = {k: i for i, (k, _) in enumerate(sorted(amt.items(), key=lambda kv: -kv[1][0]), 1)}
        cut[label] = {k: {'量': v, '占比': v / tot * 100, '名次': rank[k], '根数': m, '根': rs} for k, (v, m, rs) in amt.items()}
    ALL[name] = {'键位名次': krank, '口径': cut,
                 '根排名': [{'名次': i, '根': r, '键': KEY[r]} for i, (r, _) in enumerate(shape.most_common(), 1)]}
    print('\n══════════ %s 字 ══════════' % name)
    print('键 │ 键位名次 │ 全部根        前50%根       前30%根      │ 名次变动    头部根')
    for k in sorted(cut['全部'], key=lambda x: cut['全部'][x]['名次']):
        a, b, c3 = cut['全部'][k], cut['前 50%'][k], cut['前 30%'][k]
        print('%s  │   %2d    │ %5.2f%% 第%2d  %5.2f%% 第%2d  %5.2f%% 第%2d │ %+3d → %+3d  │ %s'
              % (k, krank[k], a['占比'], a['名次'], b['占比'], b['名次'], c3['占比'], c3['名次'],
                 a['名次'] - b['名次'], a['名次'] - c3['名次'],
                 '、'.join('%s(第%d)' % (r, srank[r]) for r in c3['根'][:6])))
json.dump(ALL, open(H + '/头部负担.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s/头部负担.json' % H)
