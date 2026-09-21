# -*- coding: utf-8 -*-
"""杠杆验证：避重若按词频加权，压力还剩多少？（2026-09-18）

3.8 的撞词是「按码位计数」——撞一个冷僻词和撞「我们」算一样重。
但实际打字里，和冷僻词同码几乎无感（让位规则会把字排前面），和高频词同码才真难受。
如果搬根新增的那些碰撞绝大多数落在冷僻词上，那「避重压力」就是被计数口径放大的，
布局其实有比 3.8 所显示的更大的活动空间。这条是可以改的杠杆，且不需要动编码规则。
"""
import io, sys, os, re, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
KEYS = 'abcdefghijklmnopqrstuvwxyz'
# ── 词频 ──
WFREQ = {}
for fn in ('08_词库与词频重建/二字词60000_自动分流.jsonl',):
    for l in open(W + '/' + fn, encoding='utf-8'):
        try: d = json.loads(l)
        except Exception: continue
        src = d.get('各源原始词频') or {}
        v = src.get('bcc_balanced') or 0
        if not v: v = max(src.values()) if src else 0
        if v: WFREQ[d['词']] = max(WFREQ.get(d['词'], 0), float(v))
print('词频覆盖 %d 条二字词' % len(WFREQ))
# ── 字频 / 拆分 / 码表 ──
freq = {}; order = []
for l in open(W + '/30_形码盒子1.0复测/默认字频.txt', encoding='utf-8-sig'):
    p = l.rstrip('\r\n').split('\t')
    if len(p) == 2 and p[1].isdigit(): freq[p[0]] = int(p[1]); order.append(p[0])
irr = json.load(open(W + '/83_单字表重放/无理码表.json', encoding='utf-8-sig'))
IRRALL = {(t, c) for g in ('容错码', '特殊简码', '无理码') for c, t in irr[g].items()}
q = open(W + '/65_群友离线工具包/夜莺2.0离线工具包/拆分查询.html', encoding='utf-8-sig').read()
D = json.JSONDecoder().raw_decode(q[re.search(r'\bconst D\s*=\s*', q).end():])[0]
KEY0 = {}; GRP = {}
for c, d in D.items():
    for r in d.get('根', []): KEY0[r['根']] = r['键']; GRP[r['根']] = r['组']
WORD = collections.defaultdict(list)
for l in open(W + '/00_维护/主表/夜莺2.0字词表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t')
    if len(t) > 1: WORD[c].append(t)
BASE = []
for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t')
    if len(c) == 4 and len(t) == 1 and (t, c) not in IRRALL and D.get(t, {}).get('根'):
        BASE.append((t, c[:2]))
wf = lambda t: freq.get(t, 0)
# 词的分档：按 bcc 词频排名
ranked = sorted(WFREQ.items(), key=lambda x: -x[1])
WRANK = {w: i + 1 for i, (w, _) in enumerate(ranked)}
def band(w):
    r = WRANK.get(w)
    if r is None: return '未登录/低频'
    if r <= 2000: return '前 2000'
    if r <= 10000: return '2001–10000'
    if r <= 30000: return '10001–30000'
    return '30000 以后'
BANDS = ['前 2000', '2001–10000', '10001–30000', '30000 以后', '未登录/低频']

def collisions(KEY):
    """返回 单字全码 → 该码上的词列表（即该字要和哪些词抢码位）"""
    out = []
    for t, sp in BASE:
        rs = D[t]['根']
        c = sp + KEY[rs[0]['根']] + KEY[rs[-1]['根']]
        ws = WORD.get(c)
        if ws: out.append((t, c, ws))
    return out

def profile(KEY):
    cs = collisions(KEY)
    n = len(cs)
    byband = collections.Counter()
    wsum = 0.0
    for t, c, ws in cs:
        for w in ws:
            byband[band(w)] += 1
            wsum += WFREQ.get(w, 0)
    return n, byband, wsum, {(t, c) for t, c, _ in cs}

n0, b0, w0, set0 = profile(KEY0)
print('\n基线：单字全码撞词 %d 处，涉及词次 %d，词频总量 %.3g' % (n0, sum(b0.values()), w0))
print('  分档：' + '  '.join('%s %d' % (b, b0[b]) for b in BANDS))

print('\n' + '═' * 76)
print('把「横」组搬到各键：新增的碰撞落在哪个词频档')
print('═' * 76)
print('  落点  新增碰撞  其中前2000  2001-1万  1万-3万  3万后  未登录   新增词频量占基线')
forms = [x for x in GRP if GRP[x] == '横']
rows = []
for dst in ('i', 'u', 'e', 'j', 'd', 'r', 'a', 'o', 't'):
    K = dict(KEY0)
    for r in forms: K[r] = dst
    n, b, w, s = profile(K)
    new = s - set0
    nb = collections.Counter()
    nw = 0.0
    for t, c in new:
        for x in WORD[c]:
            nb[band(x)] += 1; nw += WFREQ.get(x, 0)
    rows.append((dst, len(new), nb, nw))
    print('   %s   %+5d    %5d   %7d  %7d  %6d  %6d   %6.2f%%'
          % (dst, len(new), nb['前 2000'], nb['2001–10000'], nb['10001–30000'],
             nb['30000 以后'], nb['未登录/低频'], nw / w0 * 100))
print('\n解读：若「新增碰撞」几乎全部落在低频与未登录档，说明按码位计数的避重压力被放大了。')
json.dump({'基线撞词': n0, '基线分档': dict(b0), '基线词频量': w0,
           '横组落点': [{'键': d, '新增碰撞': n, '分档': dict(b), '新增词频量占基线%': round(w / w0 * 100, 3)}
                      for d, n, b, w in rows]},
          open(H + '/按词频加权避重.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s/按词频加权避重.json' % H)
