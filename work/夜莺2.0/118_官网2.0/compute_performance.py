# -*- coding: utf-8 -*-
"""官网 2.0 性能数据：从 113 最终表 + 32 字频 + 54/frozen 当量表与字音基准 + 08 词频 重算。
口径：每字取"主读音最短输入"（同 59）；键数含空格/选重键；候选位按最终表整个码位（含词）计；
      码长分布、选重、全码重按字频档计数，加权按 32 的每百万预计次数；键位负担/左右手/互击/跨排按字频加权统计各键对。
字词冲突：字频前1500 的字的全码 × 08 综合排名前 10000 的四码词 同码 → 冲突对；再按"剔除有简码的字"复算（与 1.0 网站口径一致）。"""
import io, sys, os, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__)); F = W + '/54_补删鹿旁保留羊南心四起点试跑/frozen'
J = lambda p: json.load(open(p, encoding='utf-8-sig'))
# 最终表
bycode = collections.OrderedDict(); codes = collections.defaultdict(list)
for l in open(W + '/00_维护/主表/夜莺2.0字词表.txt', encoding='utf-8-sig'):
    p = l.rstrip('\r\n').split('\t')
    if len(p) >= 2:
        bycode.setdefault(p[1], []).append(p[0])
        if len(p[0]) == 1: codes[p[0]].append(p[1])
pos = {(t, k): i + 1 for k, ts in bycode.items() for i, t in enumerate(ts)}
# 字频
ft = J(W + '/32_多来源字频重建/试验整字频率.json')['字表']
rank = {r['字']: r['新排名'] for r in ft}; wt = {r['字']: r['每百万核心字预计次数'] for r in ft}
# 当量
eq = {}
for l in open(F + '/当量表.tsv', encoding='utf-8'):
    if '\t' in l:
        k, v = l.rstrip('\n').split('\t')
        if len(k) == 2: eq[k] = float(v)
pron = collections.defaultdict(list)
for r in J(F + '/字音基准.json'): pron[r['字']].append(r)
def calc(c, k):
    p = pos[(c, k)]; seq = k + '=' * ((p - 1) // 3) + [' ', ';', "'"][(p - 1) % 3]
    costs = [eq[seq[i:i + 2]] for i in range(len(seq) - 1)]
    return {'码': k, '候选位': p, '键数': len(seq), '当量': sum(costs) / len(costs), '总成本': sum(costs)}
LEFT = set('qwertasdfgzxcvb'); FINGER = {}
for keys, f in [('qaz', 'L5'), ('wsx', 'L4'), ('edc', 'L3'), ('rfvtgb', 'L2'), ('yhnujm', 'R2'), ('ik', 'R3'), ('ol', 'R4'), ('p', 'R5')]:
    for k in keys: FINGER[k] = f
ROW = {k: r for r, keys in enumerate(['qwertyuiop', 'asdfghjkl', 'zxcvbnm']) for k in keys}
chars = []
for c, ks in codes.items():
    if c not in rank or not pron[c]: continue
    main = max(pron[c], key=lambda r: r.get('自然频率', r['频率']))
    av = [k for k in ks if k.startswith(main['音码']) or (len(k) == 1 and main['音码'].startswith(k)) or (c == '六' and k == 'lqq')] or ks
    chosen = min([calc(c, k) for k in av], key=lambda x: (x['键数'], x['候选位'], len(x['码']), x['码']))
    full = [k for k in av if len(k) == 4] or [k for k in ks if len(k) == 4]
    fullpos = min(pos[(c, k)] for k in full) if full else 1
    chars.append({'字': c, '排名': rank[c], '权': wt[c], '有简码': any(len(k) < 4 for k in ks), '全码重': fullpos > 1, **chosen})
chars.sort(key=lambda r: r['排名'])
SCOPES = [('1–300', 1, 300), ('301–500', 301, 500), ('501–1500', 501, 1500), ('1501–3000', 1501, 3000), ('3001–6000', 3001, 6000)]
def stat(rows):
    n = len(rows); tw = sum(r['权'] for r in rows)
    cnt = [sum(1 for r in rows if len(r['码']) == L) for L in (1, 2, 3, 4)]
    wcnt = [sum(r['权'] for r in rows if len(r['码']) == L) / tw * 100 for L in (1, 2, 3, 4)]
    sel = sum(1 for r in rows if r['候选位'] > 1); wsel = sum(r['权'] for r in rows if r['候选位'] > 1) / tw * 100
    fd = sum(1 for r in rows if r['全码重']); wfd = sum(r['权'] for r in rows if r['全码重']) / tw * 100
    kl = sum(r['权'] * r['键数'] for r in rows) / tw; ce = sum(r['权'] * r['总成本'] for r in rows) / tw; ke = sum(r['权'] * r['当量'] for r in rows) / tw
    pairs = alt = big = small = 0.0
    for r in rows:
        k = r['码']
        for i in range(len(k) - 1):
            a, b = k[i], k[i + 1]; pairs += r['权']
            if (a in LEFT) != (b in LEFT): alt += r['权']
            elif a != b and FINGER[a] == FINGER[b]:
                d = abs(ROW[a] - ROW[b])
                if d >= 2: big += r['权']
                elif d == 1: small += r['权']
    return {'字数': n, '码长字数': cnt, '码长加权%': [round(x, 2) for x in wcnt], '选重': sel, '选重加权%': round(wsel, 3), '全码重': fd, '全码重加权%': round(wfd, 2),
            '加权键长': round(kl, 2), '加权字均当量': round(ce, 2), '加权键均当量': round(ke, 3),
            '左右互击%': round(alt / pairs * 100, 2), '同指大跨排%': round(big / pairs * 100, 2), '同指小跨排%': round(small / pairs * 100, 2)}
rows = []
for name, a, b in SCOPES: rows.append({'scope': name, **stat([r for r in chars if a <= r['排名'] <= b])})
rows.insert(3, {'scope': '前1500字', **stat([r for r in chars if r['排名'] <= 1500])})
rows.append({'scope': '前3000字', **stat([r for r in chars if r['排名'] <= 3000])})
rows.append({'scope': '前6000字', **stat([r for r in chars if r['排名'] <= 6000])})
# 键位负担（前 6000 字，字频加权，只数字母键）
load = collections.Counter(); tot = 0.0
for r in chars:
    if r['排名'] <= 6000:
        for ch in r['码']: load[ch] += r['权']; tot += r['权']
keyboard = {k: round(load[k] / tot * 100, 2) for k in 'abcdefghijklmnopqrstuvwxyz'}
hands = [round(sum(v for k, v in keyboard.items() if k in LEFT), 2)]; hands.append(round(100 - hands[0], 2))
# 字词冲突
wrank = {}
for line in open(W + '/08_词库与词频重建/综合词表_审计候选.jsonl', encoding='utf-8'):
    d = json.loads(line); w = d.get('词') or d.get('word') or d.get('文本')
    if w and w not in wrank and d.get('综合排名'): wrank[w] = d['综合排名']
top = {r['字'] for r in chars if r['排名'] <= 1500}; noshort = {r['字'] for r in chars if r['排名'] <= 1500 and not r['有简码']}
def conflicts(charset):
    out = []
    for k, ts in bycode.items():
        if len(k) != 4: continue
        cs = [t for t in ts if len(t) == 1 and t in charset]; ws = [t for t in ts if len(t) > 1 and wrank.get(t, 10**9) <= 10000]
        for c in cs:
            for w in ws: out.append([c, k, w, rank[c], wrank[w], pos[(c, k)], pos[(w, k)]])
    return sorted(out, key=lambda x: (x[3], x[4]))
full_c = conflicts(top); filt_c = conflicts(noshort)
allpairs = sum(1 for k, ts in bycode.items() if len(k) == 4 for t in ts if len(t) == 1 and t in rank for u in ts if len(u) > 1)
data = {'version': '2.0', 'date': '2026-09-16', 'source': '113 最终表 + 32 多来源字频 + 54/frozen 当量表、字音基准 + 08 综合词频；脚本 work/夜莺2.0/118_官网2.0/compute_performance.py',
        'note': '每字取主读音最短输入；键数含空格或选重键；候选位按最终表整个码位（含词）；加权按每百万核心字预计次数；手感三项按字内相邻键对字频加权。',
        'rows': rows, 'keyboard': keyboard, 'hands': hands,
        'conflict': {'口径': '字频前1500的字的全码 × 08综合排名前10000的四码词，同码计一对', '全部单字全码': len(full_c), '剔除有简码的字': len(filt_c),
                     '前1500字中无简码的字数': len(noshort), '全表字词同码对（不限频次）': allpairs, '剩余': filt_c, '全部': full_c}}
json.dump(data, open(H + '/performance-data.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for r in rows: print(r['scope'], r['字数'], r['码长字数'], '选重', r['选重'], '%.3f%%' % r['选重加权%'], '全码重', r['全码重'], '键长', r['加权键长'], '互击', r['左右互击%'])
print('hands', hands, 'top keys', sorted(keyboard.items(), key=lambda t: -t[1])[:5])
print('冲突 全部 %d → 剔除有简码 %d；无简码字 %d；剩余样例 %s' % (len(full_c), len(filt_c), len(noshort), filt_c[:6]))
