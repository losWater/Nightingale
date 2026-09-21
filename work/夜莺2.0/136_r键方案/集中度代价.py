# -*- coding: utf-8 -*-
"""集中度到底有没有物理代价？（2026-09-18）

背景更正：退火清单显示——
  · 字词避重是「软碰撞系数」（历史 0.1），不是硬约束；
  · 「音末到首形」当量已带权 0.25，优化器看得见进入字根键的那一跳；
  · 但「键位负担……不擅自增加未经校准的惩罚权重」——集中度只报告、不计分。
所以问题不是「优化器看不见字根当量」，而是「集中度没有价格」。
本脚本查：集中度的物理代价走哪条通道——同指、同键连击、小指负担。
若 p 在这几项上确实超标，那该加的指标就不是凭空的「字根层成本」，
而是把清单里已经在报告的同指／小指项真正计权。
"""
import io, sys, os, re, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
KEYS = 'abcdefghijklmnopqrstuvwxyz'
FINGER = {}
for ks, f in (('qaz', 'L小'), ('wsx', 'L无'), ('edc', 'L中'), ('rfvtgb', 'L食'),
              ('yhnujm', 'R食'), ('ik,', 'R中'), ('ol.', 'R无'), ('p;/', 'R小')):
    for k in ks: FINGER[k] = f
ROW = {}
for ks, r in (('qwertyuiop', 1), ('asdfghjkl', 2), ('zxcvbnm', 3)):
    for k in ks: ROW[k] = r
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
BANDS = [('前 500', 500), ('前 1500', 1500), ('前 3500', 3500)]
OUT = {}
for name, n in BANDS:
    sub = [(t, freq[t]) for t in order[:n] if t in best and freq.get(t)]
    tw = sum(f for _, f in sub)
    same_f = collections.Counter()      # 同指异键（跨排）加权
    same_k = collections.Counter()      # 同键连击
    pinky = collections.Counter()       # 小指按键量
    pairs_at = collections.Counter()    # 各键参与的同指对
    tot_pair = 0
    for t, f in sub:
        c = best[t]
        for i in range(len(c) - 1):
            a, b = c[i], c[i + 1]
            tot_pair += f
            if a == b: same_k[a] += f; same_f[FINGER[a]] += f; pairs_at[a] += f
            elif FINGER[a] == FINGER[b]:
                same_f[FINGER[a]] += f; pairs_at[a] += f; pairs_at[b] += f
        for ch in c:
            if FINGER[ch] in ('L小', 'R小'): pinky[ch] += f
    tot_press = sum(len(best[t]) * f for t, f in sub)
    OUT[name] = {
        '同指率%': sum(same_f.values()) / tot_pair * 100,
        '同键连击率%': sum(same_k.values()) / tot_pair * 100,
        '各指同指量': {k: v / tot_pair * 100 for k, v in same_f.items()},
        '小指负担%': sum(pinky.values()) / tot_press * 100,
        '各小指键': {k: v / tot_press * 100 for k, v in pinky.items()},
        'p参与同指对%': pairs_at['p'] / tot_pair * 100,
        '各键同指参与': {k: pairs_at[k] / tot_pair * 100 for k in KEYS},
    }
    o = OUT[name]
    print('\n' + '═' * 70)
    print('══════ %s 字（打简口径）══════' % name)
    print('  整体同指率 %.2f%%   其中同键连击 %.2f%%' % (o['同指率%'], o['同键连击率%']))
    print('  各指的同指量：' + '  '.join('%s %.2f%%' % (k, v) for k, v in sorted(o['各指同指量'].items(), key=lambda x: -x[1])))
    print('  小指总负担 %.2f%%   分键：%s' % (o['小指负担%'],
          '  '.join('%s %.2f%%' % (k, v) for k, v in sorted(o['各小指键'].items(), key=lambda x: -x[1]))))
    top = sorted(o['各键同指参与'].items(), key=lambda x: -x[1])
    print('  参与同指最多的键：' + '  '.join('%d.%s %.2f%%' % (i, k, v) for i, (k, v) in enumerate(top[:8], 1)))
    pr = [i for i, (k, _) in enumerate(top, 1) if k == 'p'][0]
    print('  → p 参与同指 %.2f%%，排第 %d' % (o['p参与同指对%'], pr))
json.dump(OUT, open(H + '/集中度代价.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s/集中度代价.json' % H)
