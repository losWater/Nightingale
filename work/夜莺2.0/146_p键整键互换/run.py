# -*- coding: utf-8 -*-
"""p 键上的全部字根与另一个键上的全部字根整体互换，看哪一个键换完损失最小（2026-09-22 你的想法）。只读。
整键互换 = 字根层把两个字母对调，双拼码不动。所以：
  · 单字重码、三简重码结构完全不变（谁跟谁共键没变）；
  · 会变的只有：字词避重（词码是纯双拼，固定不动）、跨层当量（双拼末码→首根）、形码层当量（首根→末根）。
口径沿用 136（谁主导了布局.py）：当量取前 3500 字按字频加权；撞词按全表单字全码计数，另按词频加权。
另统计：要改全码的字数（首根或末根落在这两个键上的字），这是对老用户的代价。
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
IRR = {(t, c) for g in ('容错码', '特殊简码', '无理码') for c, t in irr[g].items()}
s = open(W + '/65_群友离线工具包/夜莺啾啾工具箱.html', encoding='utf-8-sig').read()
v = json.JSONDecoder().raw_decode(s[re.search(r'\b(?:const|let) views\s*=\s*', s).end():])[0]['query']
D = json.JSONDecoder().raw_decode(v[re.search(r'\bconst D\s*=\s*', v).end():])[0]
KEY0 = {}
for c, d in D.items():
    for r in d.get('根', []): KEY0[r['根']] = r['键']
EQ = {}
for l in open(W + '/54_补删鹿旁保留羊南心四起点试跑/frozen/当量表.tsv', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) >= 2:
        try: EQ[p[0]] = float(p[1])
        except ValueError: pass
eq = lambda a, b: EQ.get(a + b, 1.3)
WF = {}
for l in open(W + '/08_词库与词频重建/二字词60000_自动分流.jsonl', encoding='utf-8'):
    try: d = json.loads(l)
    except Exception: continue
    sr = d.get('各源原始词频') or {}
    x = sr.get('bcc_balanced') or (max(sr.values()) if sr else 0)
    if x: WF[d['词']] = float(x)
WORD = collections.defaultdict(list)
for l in open(W + '/00_维护/主表/夜莺2.0字词表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t')
    if len(t) > 1: WORD[c].append(t)
full = {}; ALL = []
for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t')
    if len(c) == 4 and len(t) == 1 and (t, c) not in IRR and D.get(t, {}).get('根'):
        ALL.append((t, c[:2]))
        full.setdefault(t, c)
SAMP = [(t, full[t][:2], D[t]['根']) for t in order[:3500] if t in full and freq.get(t)]
def metrics(swap):
    k = lambda r: swap.get(KEY0[r], KEY0[r])
    b = cc = w = 0.0
    for t, sp, rs in SAMP:
        f = freq[t]; w += f; k3, k4 = k(rs[0]['根']), k(rs[-1]['根'])
        b += f * eq(sp[1], k3); cc += f * eq(k3, k4)
    n = 0; wm = 0.0; moved = 0
    for t, sp in ALL:
        rs = D[t]['根']; code = sp + k(rs[0]['根']) + k(rs[-1]['根'])
        if code != sp + KEY0[rs[0]['根']] + KEY0[rs[-1]['根']]: moved += 1
        ws = WORD.get(code)
        if ws: n += 1; wm += sum(WF.get(x, 0) for x in ws)
    return b / w, cc / w, n, wm, moved
B = metrics({})
print('现状：跨层当量 %.4f  形码层当量 %.4f  合计 %.4f  撞词 %d 处（词频量 %.4g）\n'
      % (B[0], B[1], B[0] + B[1], B[2], B[3]))
rows = []
for x in KEYS:
    if x == 'p': continue
    m = metrics({'p': x, x: 'p'})
    rows.append((x, m[0] - B[0], m[1] - B[1], (m[0] + m[1]) - (B[0] + B[1]), m[2] - B[2], (m[3] - B[3]) / B[3] * 100, m[4]))
print('p 与各键整键互换（按「当量合计变化」从好到坏；负数 = 变好）')
print('  键   跨层Δ     形码层Δ   当量合计Δ   撞词Δ   撞词词频量Δ   要改码的字')
for x, a, b, t, n, wm, mv in sorted(rows, key=lambda r: r[3]):
    print('  %s   %+.4f   %+.4f   %+.4f     %+5d    %+6.2f%%       %d' % (x, a, b, t, n, wm, mv))
good = [r for r in rows if r[3] < 0 and r[4] <= 0 and r[5] <= 0]
print('\n当量、撞词、撞词词频量三项都不变差的：%s' % ('、'.join(r[0] for r in good) if good else '没有'))
json.dump({'现状': B, '互换': [dict(zip(('键', '跨层Δ', '形码层Δ', '当量合计Δ', '撞词Δ', '撞词词频量Δ%', '改码字数'), r)) for r in rows]},
          open(H + '/结果.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
