# -*- coding: utf-8 -*-
"""按键热力（2026-09-17 你要）：打简的前提下，各键的按键次数排名。
字频用形码盒子 1.0 的默认字频（30_形码盒子1.0复测/默认字频.txt，6000 字）。
打简 = 每个字用它最短的正式码（一简 → 二简 → 三简 → 全码）；容错码与特殊简码不算，它们是额外入口不是常打路径。
多音字取最短的那个码；同长度时取码表里靠前的（即候选序靠前的读音）。
分档：前 500、前 1500、前 3500（累计，你定）。"""
import io, sys, os, json, collections
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
miss = [t for t, _ in freq if t not in best]
print('形码盒子默认字频 %d 字；夜莺没收的 %d 个（已跳过）：%s' % (len(freq), len(miss), '、'.join(miss)))
BANDS = [('前 500', 500), ('前 1500', 1500), ('前 3500', 3500)]
ROWS = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm']
FINGER = {**{k: '左小' for k in 'qaz'}, **{k: '左无' for k in 'wsx'}, **{k: '左中' for k in 'edc'}, **{k: '左食' for k in 'rfvtgb'},
          **{k: '右食' for k in 'yhnujm'}, **{k: '右中' for k in 'ik'}, **{k: '右无' for k in 'ol'}, **{k: '右小' for k in 'p'}}
out = []
for name, n in BANDS:
    cnt = collections.Counter(); total = 0; wsum = 0
    for t, f in freq[:n]:
        c = best.get(t)
        if not c: continue
        for ch in c: cnt[ch] += f
        total += f * len(c); wsum += f
    out.append((name, n, cnt, total, wsum, total / wsum))
    print('\n══════ %s 字 ══════  加权总按键 %d，平均码长 %.3f' % (name, total, total / wsum))
    print('排名  键  按键次数        占比    手指')
    for i, (k, v) in enumerate(cnt.most_common(), 1):
        print('%3d   %s  %12d  %6.2f%%   %s' % (i, k, v, v / total * 100, FINGER.get(k, '?')))
    pos = {k: i for i, (k, _) in enumerate(cnt.most_common(), 1)}
    print('\n  键盘热力（数字＝本档排名）：')
    for r, row in enumerate(ROWS):
        print('   ' + '  ' * r + ' '.join('%s%-2d' % (k, pos.get(k, 0)) for k in row))
    fg = collections.Counter()
    for k, v in cnt.items(): fg[FINGER.get(k, '?')] += v
    print('  手指分布：' + '  '.join('%s %.1f%%' % (f, v / total * 100) for f, v in sorted(fg.items(), key=lambda x: -x[1])))
    lh = sum(v for k, v in cnt.items() if k in 'qwertasdfgzxcvb')
    print('  左手 %.1f%%，右手 %.1f%%' % (lh / total * 100, 100 - lh / total * 100))
ranks = [{k: (i, v) for i, (k, v) in enumerate(cn.most_common(), 1)} for _, _, cn, _, _, _ in out]
tot = [t for _, _, _, t, _, _ in out]
print('\n\n══════ 三档对照（按前 1500 的名次排）══════')
print('%-4s %-20s %-20s %-20s %s' % ('键', '前 500', '前 1500', '前 3500', '手指'))
for k in sorted('abcdefghijklmnopqrstuvwxyz', key=lambda x: ranks[1].get(x, (99, 0))[0]):
    cells = ['第 %-2d 名 %6.2f%%' % (ranks[j].get(k, (0, 0))[0], ranks[j].get(k, (0, 0))[1] / tot[j] * 100) for j in range(3)]
    print('%-4s %-20s %-20s %-20s %s' % (k, cells[0], cells[1], cells[2], FINGER.get(k, '?')))
print('\n名次变动（前 500 → 前 3500）：')
mv = [(k, ranks[0].get(k, (99, 0))[0], ranks[2].get(k, (99, 0))[0]) for k in 'abcdefghijklmnopqrstuvwxyz']
for k, a, b in sorted(mv, key=lambda x: x[1] - x[2]):
    if a != b: print('   %s  第 %d 名 → 第 %d 名  （%s %d 位）' % (k, a, b, '升' if b < a else '降', abs(a - b)))
json.dump({'字频来源': '形码盒子 1.0 默认字频（6000 字）', '口径': '打简：每字取最短正式码；容错码与特殊简码不计；多音字取最短、同长取码表靠前',
           '夜莺未收': miss,
           '分档': [{'档': n, '字数': c, '加权总按键': t, '平均码长': round(a, 4),
                    '键位排名': [{'名次': i, '键': k, '次数': v, '占比': round(v / t * 100, 3), '手指': FINGER.get(k, '?')}
                               for i, (k, v) in enumerate(cn.most_common(), 1)]}
                   for n, c, cn, t, w, a in out]},
          open(H + '/按键热力.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s/按键热力.json' % H)
