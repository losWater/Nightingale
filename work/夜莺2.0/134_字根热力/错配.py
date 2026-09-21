# -*- coding: utf-8 -*-
"""键位与字根的错配分析（2026-09-17）。

群里跟打高手指出：键位热力低不代表键上的根用得少。实例——p 键按键位排倒数第二，
但它扛着全局排名第 10 的「横」，而且 30 个根挤在一起。本脚本把这种错配量化。

指标（都按同一档字频加权）：
  键位量    该键在全部按键里的占比（含双拼那两码）——就是退火看的那个数
  形码量    该键作为字根键被敲到的占比——真实的字根负担
  根数      该键上实际被用到的根形个数
  头根      该键上最大的那个根，及它在全局 403 根里的名次
  前30/前50 该键上有几个根进了全局前 30 / 前 50
  均名次    该键上各根全局名次的加权平均（按使用量加权）——越小说明扛的越是高频根
  错配      键位名次 − 形码量名次，正数＝键位热力低估了这个键
"""
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
BANDS = [('前 500', 500), ('前 1500', 1500), ('前 3500', 3500)]
ALL = {}
for name, n in BANDS:
    keys = collections.Counter()          # 键位量（含双拼）
    shape = collections.Counter()         # 根形量
    bykey = collections.defaultdict(collections.Counter)
    for t, f in freq[:n]:
        c = best.get(t)
        if not c: continue
        for ch in c: keys[ch] += f
        if len(c) < 3: continue
        rs = D.get(t, {}).get('根')
        if not rs: continue
        for r in [rs[0]['根']] + ([rs[-1]['根']] if len(c) == 4 else []):
            shape[r] += f; bykey[KEY[r]][r] += f
    ktot = sum(keys.values()); stot = sum(shape.values())
    krank = {k: i for i, (k, _) in enumerate(keys.most_common(), 1)}
    srank = {r: i for i, (r, _) in enumerate(shape.most_common(), 1)}
    fkey = collections.Counter({k: sum(v.values()) for k, v in bykey.items()})
    frank = {k: i for i, (k, _) in enumerate(fkey.most_common(), 1)}
    rows = []
    for k in 'abcdefghijklmnopqrstuvwxyz':
        cnt = bykey.get(k, collections.Counter()); s = sum(cnt.values())
        if not s: continue
        head, hv = cnt.most_common(1)[0]
        avg = sum(srank[r] * v for r, v in cnt.items()) / s
        rows.append({'键': k, '键位量': keys[k] / ktot * 100, '键位名次': krank[k],
                     '形码量': s / stot * 100, '形码名次': frank[k], '根数': len(cnt),
                     '头根': head, '头根名次': srank[head], '头根占本键': hv / s * 100,
                     '前30': sum(1 for r in cnt if srank[r] <= 30), '前50': sum(1 for r in cnt if srank[r] <= 50),
                     '均名次': avg, '错配': krank[k] - frank[k]})
    ALL[name] = {'键': rows, '根排名': [{'名次': i, '根': r, '键': KEY[r], '组': GROUP[r], '占比': round(v / stot * 100, 3)} for i, (r, v) in enumerate(shape.most_common(), 1)]}
    print('\n══════════ %s 字 ══════════' % name)
    print('键  键位量   名次 │ 形码量   名次 │ 错配 │ 根数  头根(全局名次, 占本键)      前30 前50  均名次')
    for r in sorted(rows, key=lambda x: -x['错配']):
        print('%s   %5.2f%%  %2d  │ %5.2f%%  %2d  │ %+3d  │ %3d   %-4s第 %-3d 名 %4.0f%%        %d    %d   %6.1f'
              % (r['键'], r['键位量'], r['键位名次'], r['形码量'], r['形码名次'], r['错配'], r['根数'],
                 r['头根'], r['头根名次'], r['头根占本键'], r['前30'], r['前50'], r['均名次']))
    top = ALL[name]['根排名'][:20]
    byk = collections.Counter(r['键'] for r in top)
    print('\n  全局前 20 的根落在哪些键上：' + '  '.join('%s×%d' % (k, v) for k, v in byk.most_common()))
    print('  ' + '、'.join('%s(%s,第%d)' % (r['根'], r['键'], r['名次']) for r in top))
json.dump(ALL, open(H + '/键根错配.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s/键根错配.json' % H)
