# -*- coding: utf-8 -*-
"""字根热力（2026-09-17 群里跟打高手提的：键位使用率低，不代表键上的根使用率低——
若某键的量全来自一个根，那个根其实是高频根。这是退火只看键位的盲点）。

口径：
  · 字频用形码盒子 1.0 的默认字频（6000 字）。
  · 打简：每个字取最短的正式码（容错码、特殊简码不计）。字根只在实际被打出来时才计数——
      码长 1、2（一简/二简）：不用形码，字根不计；
      码长 3（三简）：只用首根；
      码长 4（全码）：首根 + 末根。
  · 两套口径分别排名：130 组（归并后）与 403 根形（不归并）。
  · 分档：前 500、前 1500、前 3500。
另出「每个键的量由哪些根贡献」，直接回答那位的问题。"""
import io, sys, os, re, json, collections
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
print('字频 %d 字；拆分 %d 字；根形 %d 个，归并后 %d 组' % (len(freq), len(D), len(KEY), len(set(GROUP.values()))))
GKEY = {}
for r, g in GROUP.items(): GKEY.setdefault(g, set()).add(KEY[r])
cross = {g: ks for g, ks in GKEY.items() if len(ks) > 1}
GKEY = {g: '／'.join(sorted(ks)) for g, ks in GKEY.items()}
print('跨键的组：%d 个%s' % (len(cross), '  ' + '、'.join('%s→%s' % (g, '/'.join(sorted(k))) for g, k in list(cross.items())[:6]) if cross else '（每组都只在一个键上）'))
BANDS = [('前 500', 500), ('前 1500', 1500), ('前 3500', 3500)]
res = {}
for name, n in BANDS:
    shape = collections.Counter(); group = collections.Counter(); bykey = collections.defaultdict(collections.Counter)
    total = 0; nocode = 0; nosplit = 0; bylen = collections.Counter()
    for t, f in freq[:n]:
        c = best.get(t)
        if not c: nocode += f; continue
        bylen[len(c)] += f
        if len(c) < 3: continue                      # 一简、二简不碰形码
        rs = D.get(t, {}).get('根')
        if not rs: nosplit += f; continue
        用 = [rs[0]['根']] + ([rs[-1]['根']] if len(c) == 4 else [])      # 三简只用首根；全码首末都用
        for r in 用:
            shape[r] += f; group[GROUP[r]] += f; bykey[KEY[r]][r] += f; total += f
    res[name] = {'根形': shape, '组': group, '按键': bykey, '总': total, '码长': bylen, '无拆分': nosplit}
    print('\n══════ %s 字 ══════  形码按键加权总数 %d' % (name, total))
    print('  各码长的字频占比：' + '  '.join('%d 码 %.1f%%' % (k, v / sum(bylen.values()) * 100) for k, v in sorted(bylen.items())))
    for label, cnt, top in (('130 组（归并）', group, 30), ('403 根形（不归并）', shape, 30)):
        print('\n  【%s】前 %d：' % (label, top))
        for i, (r, v) in enumerate(cnt.most_common(top), 1):
            k = KEY.get(r, '') if label.startswith('403') else '／'.join(sorted({KEY[x] for x in KEY if GROUP[x] == r}))
            print('   %2d  %-18s %6.2f%%   键 %s' % (i, r, v / total * 100, k))
json.dump({'字频来源': '形码盒子 1.0 默认字频（6000 字）',
           '口径': '打简：每字取最短正式码；三简只用首根，全码用首末根；一二简不计。容错码与特殊简码不计。',
           '分档': [{'档': n, '形码按键加权总数': res[n]['总'],
                    '组排名': [{'名次': i, '组': r, '键': GKEY.get(r, ''), '占比': round(v / res[n]['总'] * 100, 3)} for i, (r, v) in enumerate(res[n]['组'].most_common(), 1)],
                    '根形排名': [{'名次': i, '根': r, '键': KEY.get(r, ''), '组': GROUP.get(r, ''), '占比': round(v / res[n]['总'] * 100, 3)}
                              for i, (r, v) in enumerate(res[n]['根形'].most_common(), 1)]} for n, _ in BANDS]},
          open(H + '/字根热力.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
# 每个键的量由哪些根贡献（回答那位的问题）
print('\n\n══════ 每个键的量由哪些根贡献（前 1500 档）══════')
r = res['前 1500']; tot = r['总']
keyrank = sorted(r['按键'].items(), key=lambda kv: -sum(kv[1].values()))
for k, cnt in keyrank:
    s = sum(cnt.values()); top = cnt.most_common()
    head = top[0]
    print('\n %s  键占形码量 %5.2f%%   该键上有 %d 个根在用，最大的一个占了本键的 %.0f%%' % (k, s / tot * 100, len(cnt), head[1] / s * 100))
    print('    ' + '  '.join('%s %.1f%%' % (x, v / s * 100) for x, v in top[:8]) + ('  …' if len(top) > 8 else ''))
json.dump({'前 1500 档': {k: {'键占形码量%': round(sum(v.values()) / tot * 100, 3),
                           '各根贡献': [{'根': x, '组': GROUP.get(x, ''), '占本键%': round(c / sum(v.values()) * 100, 2), '占全局%': round(c / tot * 100, 3)}
                                    for x, c in v.most_common()]} for k, v in keyrank}},
          open(H + '/每键的根贡献.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s/字根热力.json  与  每键的根贡献.json' % H)
