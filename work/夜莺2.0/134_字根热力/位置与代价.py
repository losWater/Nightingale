# -*- coding: utf-8 -*-
"""p 在第三位/第四位的分布，以及各键的真实代价（2026-09-17 你要）。

第三位＝首根键，第四位＝末根键。简码与全码分开列表：
  【简码表】打简后是三码的字——只有第三位。
  【全码表】每个字的全码（四码）——第三位与第四位都有。这是编码本身的分布，不看打不打简。
每档各出：字数占比（不加权）与字频占比（加权）、各键在该位的频次排名。
末尾按当量表算「真实代价」：把每个键在字根位的量，乘以它在该位的平均击键当量。"""
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
best = {t: min(cs, key=lambda c: (len(c), cs.index(c))) for t, cs in codes.items()}
EQ = {}
for l in open(W + '/54_补删鹿旁保留羊南心四起点试跑/frozen/当量表.tsv', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) >= 2:
        try: EQ[p[0]] = float(p[1])
        except ValueError: pass
KEYS = 'abcdefghijklmnopqrstuvwxyz'
BANDS = [('前 500', 500), ('前 1500', 1500), ('前 3500', 3500)]
OUT = {}
for name, n in BANDS:
    sub = [(t, f) for t, f in freq[:n] if t in best]
    tot_chars = len(sub); tot_w = sum(f for _, f in sub)
    # 简码表：打简后是三码的
    three = [(t, f, best[t]) for t, f in sub if len(best[t]) == 3]
    # 全码表：每个字的全码
    fours = [(t, f, full[t]) for t, f in sub if t in full]
    tabs = {}
    for label, rows, poss in (('简码（打简后三码）', three, [2]), ('全码（每字四码）', fours, [2, 3])):
        d = {}
        for pos in poss:
            cn = collections.Counter(); cw = collections.Counter()
            for t, f, c in rows: cn[c[pos]] += 1; cw[c[pos]] += f
            rank_w = {k: i for i, (k, _) in enumerate(cw.most_common(), 1)}
            d['第 %d 位' % (pos + 1)] = {'字数': dict(cn), '加权': dict(cw), '名次': rank_w,
                                       '总字数': len(rows), '总权': sum(f for _, f, _ in rows)}
        tabs[label] = d
    OUT[name] = {'总字数': tot_chars, '总权': tot_w, '表': tabs}
    print('\n' + '═' * 78)
    print('══════ %s 字 ══════  可统计 %d 字' % (name, tot_chars))
    for label, d in tabs.items():
        base_n = list(d.values())[0]['总字数']; base_w = list(d.values())[0]['总权']
        print('\n【%s】样本 %d 字，占本档 %.1f%%（按字频 %.1f%%）' % (label, base_n, base_n / tot_chars * 100, base_w / tot_w * 100))
        for posname, x in d.items():
            cw, cn, rk = x['加权'], x['字数'], x['名次']
            pw = cw.get('p', 0); pn = cn.get('p', 0)
            print('  %s：p 出现在 %d 字（占本表 %.2f%%），加权占比 %.2f%%，排第 %d 名'
                  % (posname, pn, pn / base_n * 100, pw / base_w * 100, rk.get('p', 0)))
            top = sorted(cw.items(), key=lambda kv: -kv[1])
            print('    该位各键排名：' + '  '.join('%d.%s %.1f%%' % (i, k, v / base_w * 100) for i, (k, v) in enumerate(top, 1)))
# 真实代价：字根位的量 × 该位的平均当量
print('\n\n' + '═' * 78)
print('══════ 真实代价（前 1500 档，按当量加权）══════')
print('当量＝相邻两键的击键成本，取自 54/frozen/当量表.tsv。字根位的代价＝进入该键的击键对当量 × 该位的量。')
sub = [(t, f) for t, f in freq[:1500] if t in best]
cost3 = collections.Counter(); cost4 = collections.Counter(); amt3 = collections.Counter(); amt4 = collections.Counter()
for t, f in sub:
    c = best[t]
    if len(c) >= 3:
        amt3[c[2]] += f; cost3[c[2]] += f * EQ.get(c[1] + c[2], 1.3)          # 第二位→第三位
    if len(c) == 4:
        amt4[c[3]] += f; cost4[c[3]] += f * EQ.get(c[2] + c[3], 1.3)          # 第三位→第四位
tc = sum(cost3.values()) + sum(cost4.values()); ta = sum(amt3.values()) + sum(amt4.values())
rows = []
for k in KEYS:
    a = amt3[k] + amt4[k]; c = cost3[k] + cost4[k]
    if a: rows.append((k, a / ta * 100, c / tc * 100, c / a, (c / tc) / (a / ta)))
print('\n键   字根量    代价占比   平均当量   代价/量  （>1 ＝ 比平均更费力）')
for k, a, c, e, ratio in sorted(rows, key=lambda x: -x[4]):
    print(' %s   %5.2f%%   %5.2f%%    %5.3f     %5.3f' % (k, a, c, e, ratio))
json.dump({'位置分布': {n: {l: {p: {'字数': x['字数'], '加权': x['加权'], '名次': x['名次']} for p, x in d.items()} for l, d in v['表'].items()} for n, v in OUT.items()},
           '真实代价_前1500': [{'键': k, '字根量%': round(a, 3), '代价占比%': round(c, 3), '平均当量': round(e, 4), '代价量比': round(r, 4)} for k, a, c, e, r in rows]},
          open(H + '/位置与代价.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s/位置与代价.json' % H)
