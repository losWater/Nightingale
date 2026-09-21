# -*- coding: utf-8 -*-
"""只看三码字：p 作为第三码（首根键）占多少（2026-09-21 你要）。

口径：打简之后**恰好是三码**的字。三码 = 双拼两码 + 首根键，所以第三位一定是首根键，
这一档最能看出「首根落在哪个键上」的真实分布，不被全码的末根稀释。
容错码与特殊简码不计（额外入口，不是常打路径）。
两种频率都给：
  字数占比——这一档里有多少个字的首根在 p；
  加权占比——按字频加权，实际敲到 p 的比重。
"""
import io, sys, os, re, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
KEYS = 'abcdefghijklmnopqrstuvwxyz'
freq = {}; order = []
for l in open(W + '/30_形码盒子1.0复测/默认字频.txt', encoding='utf-8-sig'):
    p = l.rstrip('\r\n').split('\t')
    if len(p) == 2 and p[1].isdigit(): freq[p[0]] = int(p[1]); order.append(p[0])
irr = json.load(open(W + '/83_单字表重放/无理码表.json', encoding='utf-8-sig'))
SKIP = {(t, c) for g in ('容错码', '特殊简码') for c, t in irr[g].items()}
codes = collections.defaultdict(list)
for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t')
    if (t, c) not in SKIP: codes[t].append(c)
best = {t: min(cs, key=lambda c: (len(c), cs.index(c))) for t, cs in codes.items()}
BANDS = [('前 500', 500), ('前 1500', 1500), ('前 3500', 3500), ('全部 6000', len(order))]
OUT = {}
for name, n in BANDS:
    sub = [t for t in order[:n] if t in best and freq.get(t)]
    three = [t for t in sub if len(best[t]) == 3]
    if not three: continue
    cn = collections.Counter(); cw = collections.Counter()
    for t in three:
        k = best[t][2]
        cn[k] += 1; cw[k] += freq[t]
    tn = sum(cn.values()); tw = sum(cw.values())
    rank_n = {k: i for i, (k, _) in enumerate(cn.most_common(), 1)}
    rank_w = {k: i for i, (k, _) in enumerate(cw.most_common(), 1)}
    OUT[name] = {'三码字数': tn, '占本档': len(three) / len(sub) * 100,
                 'p字数': cn['p'], 'p字数占比': cn['p'] / tn * 100, 'p字数名次': rank_n.get('p', 0),
                 'p加权占比': cw['p'] / tw * 100, 'p加权名次': rank_w.get('p', 0),
                 '字数': dict(cn), '加权': {k: cw[k] / tw * 100 for k in cw}}
    print('\n' + '═' * 74)
    print('══ %s ══  本档可统计 %d 字，其中三码字 %d 个（占 %.1f%%）'
          % (name, len(sub), len(three), len(three) / len(sub) * 100))
    o = OUT[name]
    print('  p 作为第三码：%d 个字，占三码字数的 %.2f%%（第 %d 名）；按字频加权 %.2f%%（第 %d 名）'
          % (o['p字数'], o['p字数占比'], o['p字数名次'], o['p加权占比'], o['p加权名次']))
    print('  各键在第三位的加权排名：')
    top = sorted(cw.items(), key=lambda kv: -kv[1])
    for i in range(0, len(top), 7):
        print('    ' + '   '.join('%2d.%s %5.2f%%' % (j, k, v / tw * 100)
                                  for j, (k, v) in enumerate(top[i:i + 7], i + 1)))
print('\n' + '═' * 74)
print('三档对照：p 在三码字第三位的占比')
print('  档位        三码字数   p 字数   字数占比  名次   加权占比  名次')
for name, _ in BANDS:
    if name not in OUT: continue
    o = OUT[name]
    print('  %-10s  %6d   %5d   %6.2f%%  %3d    %6.2f%%  %3d'
          % (name, o['三码字数'], o['p字数'], o['p字数占比'], o['p字数名次'], o['p加权占比'], o['p加权名次']))
json.dump(OUT, open(H + '/三码字里的p.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s/三码字里的p.json' % H)
