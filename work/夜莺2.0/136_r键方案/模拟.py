# -*- coding: utf-8 -*-
"""把 p 键上的高频根整组搬到 r，看真实代价（2026-09-18）。

论文 3.4 指出 r 是最省力的字根键（代价量比 0.913），p 是第二费力（1.062）。
本脚本回答「那你说怎么办」：逐组模拟 p → r，算出每一步的收益与代价。

模型（已对照 码表概念与规则.md）：
  全码 = 双拼两码 + KEY[首根] + KEY[末根]
  三简 = 双拼两码 + KEY[首根]          ← 所以搬首根会连带动三简
  词码 = 纯双拼，不含字根                ← 搬根不改词码，词码当作固定障碍物
约束：
  字根按「组」绑定，同组必须同键，所以只能整组搬。
第 0 步先做地基核验：用上式重算每个字的全码，必须和主表一致，否则模型不成立。
"""
import io, sys, os, re, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
KEYS = 'abcdefghijklmnopqrstuvwxyz'

# ── 读料 ──
freq = {}
order = []
for l in open(W + '/30_形码盒子1.0复测/默认字频.txt', encoding='utf-8-sig'):
    p = l.rstrip('\r\n').split('\t')
    if len(p) == 2 and p[1].isdigit(): freq[p[0]] = int(p[1]); order.append(p[0])
irr = json.load(open(W + '/83_单字表重放/无理码表.json', encoding='utf-8-sig'))
SKIP = {(t, c) for g in ('容错码', '特殊简码') for c, t in irr[g].items()}
IRRALL = set()
for g in ('容错码', '特殊简码', '无理码'):
    for c, t in irr[g].items(): IRRALL.add((t, c))

q = open(W + '/65_群友离线工具包/夜莺2.0离线工具包/拆分查询.html', encoding='utf-8-sig').read()
D = json.JSONDecoder().raw_decode(q[re.search(r'\bconst D\s*=\s*', q).end():])[0]
KEY0 = {}; GRP = {}
for c, d in D.items():
    for r in d.get('根', []): KEY0[r['根']] = r['键']; GRP[r['根']] = r['组']
GRPKEY = {}
for r, g in GRP.items(): GRPKEY.setdefault(g, set()).add(KEY0[r])
bad = {g: ks for g, ks in GRPKEY.items() if len(ks) > 1}
GRPKEY = {g: list(ks)[0] for g, ks in GRPKEY.items()}

EQ = {}
for l in open(W + '/54_补删鹿旁保留羊南心四起点试跑/frozen/当量表.tsv', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) >= 2:
        try: EQ[p[0]] = float(p[1])
        except ValueError: pass
eq = lambda a, b: EQ.get(a + b, 1.3)

rows = [l.rstrip('\n').split('\t') for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8')]
WORDCODE = collections.defaultdict(list)
for l in open(W + '/00_维护/主表/夜莺2.0字词表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t')
    if len(t) > 1: WORDCODE[c].append(t)

# ── 第 0 步：地基核验 ──
print('═' * 74)
print('第 0 步　地基核验：全码能不能由「双拼 + 首根键 + 末根键」重算出来')
print('═' * 74)
if bad: print('  !! 有组跨键，模型前提被破坏：', list(bad.items())[:3])
else: print('  组键一致性：%d 个组，每组只在一个键上 ✓' % len(GRPKEY))

def recompute(t, sp, KEY):
    rs = D.get(t, {}).get('根')
    if not rs: return None
    return sp + KEY[rs[0]['根']] + KEY[rs[-1]['根']]

full = []          # (字, 双拼, 主表全码)
ok = miss = mism = 0
mismex = []
for t, c in rows:
    if len(c) != 4 or len(t) != 1: continue
    if (t, c) in IRRALL: continue          # 无理码不由规则生成
    r = recompute(t, c[:2], KEY0)
    if r is None: miss += 1; continue
    full.append((t, c[:2], c))
    if r == c: ok += 1
    else:
        mism += 1
        if len(mismex) < 8: mismex.append((t, c, r))
print('  可重算并吻合 %d 个全码位，无拆分 %d，不吻合 %d' % (ok, miss, mism))
if mism:
    print('  不吻合样例：', '  '.join('%s 表=%s 算=%s' % x for x in mismex))
    print('  → 这些码位不进入模拟（模型只对规则生成的码位负责）')
BASE = [(t, sp, c) for t, sp, c in full if recompute(t, sp, KEY0) == c]
print('  进入模拟的全码位：%d' % len(BASE))

# ── 指标 ──
TOPN = 3500
TOP = set(order[:TOPN])
def wf(t): return freq.get(t, 0)

def measure(KEY):
    """给定键位分配，算：单字全码重码代价、三简重码代价、撞词数、p/r 的字根层代价。"""
    fullmap = collections.defaultdict(list)      # 全码 → [(字, 双拼)]
    threemap = collections.defaultdict(set)      # 三简码 → {字}
    rootamt = collections.Counter(); rootcost = collections.Counter()
    for t, sp, _ in BASE:
        rs = D[t]['根']
        k3, k4 = KEY[rs[0]['根']], KEY[rs[-1]['根']]
        fullmap[sp + k3 + k4].append(t)
        threemap[sp + k3].add(t)
        f = wf(t)
        if f:
            rootamt[k3] += f; rootcost[k3] += f * eq(sp[1], k3)
            rootamt[k4] += f; rootcost[k4] += f * eq(k3, k4)
    # 全码重码代价：同码字按字频降序，第 n 个多花 n 次翻页/选重
    dup_codes = 0; dup_cost = 0; dup_chars = 0
    for c, ts in fullmap.items():
        if len(ts) < 2: continue
        dup_codes += 1; dup_chars += len(ts) - 1
        for i, t in enumerate(sorted(ts, key=lambda x: -wf(x))):
            if i: dup_cost += wf(t) * i
    # 三简位：三简码上有多少字挤着（只看进了前 3500 的字，它们才真的用三简）
    t3_cost = 0; t3_codes = 0
    for c, ts in threemap.items():
        hot = sorted([t for t in ts if t in TOP], key=lambda x: -wf(x))
        if len(hot) < 2: continue
        t3_codes += 1
        for i, t in enumerate(hot):
            if i: t3_cost += wf(t) * i
    # 撞词：单字全码落在词码上（该码位本来归词）
    hit = [(t, c) for c, ts in fullmap.items() if c in WORDCODE for t in ts]
    hit_w = sum(wf(t) for t, _ in hit)
    tot = sum(rootamt.values()); totc = sum(rootcost.values())
    return {
        '全码重码位': dup_codes, '重码字数': dup_chars, '全码选重代价': dup_cost,
        '三简挤位': t3_codes, '三简选重代价': t3_cost,
        '撞词位': len(hit), '撞词加权': hit_w,
        '字根量': {k: rootamt[k] / tot * 100 for k in KEYS},
        '字根代价': {k: rootcost[k] / totc * 100 for k in KEYS},
        '总当量成本': totc / tot,
    }

B = measure(KEY0)
TOTF = sum(wf(t) for t, _, _ in BASE)
print('\n' + '═' * 74)
print('第 1 步　基线（现状）')
print('═' * 74)
print('  全码重码位 %d，涉及 %d 个让位字，加权选重代价 %.3f 次/字'
      % (B['全码重码位'], B['重码字数'], B['全码选重代价'] / TOTF))
print('  三简挤位 %d（前 %d 字口径），加权选重代价 %.3f 次/字' % (B['三简挤位'], TOPN, B['三简选重代价'] / TOTF))
print('  单字全码落在词码上 %d 处' % B['撞词位'])
print('  p 字根量 %.2f%%  代价 %.2f%%   |   r 字根量 %.2f%%  代价 %.2f%%'
      % (B['字根量']['p'], B['字根代价']['p'], B['字根量']['r'], B['字根代价']['r']))
print('  全键盘平均字根当量 %.4f' % B['总当量成本'])

# ── 第 2 步：p 上各组的分量 ──
pg = collections.Counter()
for t, sp, _ in BASE:
    rs = D[t]['根']
    f = wf(t)
    if not f: continue
    for r in (rs[0]['根'], rs[-1]['根']):
        if KEY0[r] == 'p': pg[GRP[r]] += f
tot_p = sum(pg.values())
print('\n' + '═' * 74)
print('第 2 步　p 键上各组的分量（可搬的最小单位）')
print('═' * 74)
print('  组                     占 p 的       占全局字根量   含根形')
for g, v in pg.most_common():
    forms = sorted([r for r in GRP if GRP[r] == g])
    print('  %-20s %6.2f%%      %5.2f%%        %s' % (g, v / tot_p * 100,
          v / sum(sum(1 for _ in []) or 0 for _ in []) if False else v / TOTF / 2 * 100,
          '、'.join(forms[:6]) + ('…' if len(forms) > 6 else '')))

# ── 第 3 步：逐组单独搬到 r ──
print('\n' + '═' * 74)
print('第 3 步　逐组单独搬到 r：每一组自己值不值')
print('═' * 74)
print('  组                   p字根量  r字根量   全码重码位  选重代价   撞词  总当量')
print('  现状                 %6.2f%% %6.2f%%   %5d     %+.4f   %4d   %.4f'
      % (B['字根量']['p'], B['字根量']['r'], B['全码重码位'], 0.0, B['撞词位'], B['总当量成本']))
single = []
for g, v in pg.most_common():
    K = dict(KEY0)
    for r in [x for x in GRP if GRP[x] == g]: K[r] = 'r'
    m = measure(K)
    d_dup = m['全码重码位'] - B['全码重码位']
    d_cost = (m['全码选重代价'] - B['全码选重代价']) / TOTF
    d_word = m['撞词位'] - B['撞词位']
    single.append((g, v, m, d_dup, d_cost, d_word))
    print('  %-18s %6.2f%% %6.2f%%   %5d(%+d) %+.4f   %4d(%+d) %.4f'
          % (g, m['字根量']['p'], m['字根量']['r'], m['全码重码位'], d_dup,
             d_cost, m['撞词位'], d_word, m['总当量成本']))
json.dump({'基线': {k: v for k, v in B.items() if not isinstance(v, dict)},
           'p各组分量': {g: v for g, v in pg.most_common()},
           '逐组': [{'组': g, '量': v, 'p字根量': m['字根量']['p'], 'r字根量': m['字根量']['r'],
                    '全码重码位': m['全码重码位'], 'Δ重码位': d, 'Δ选重代价': c, 'Δ撞词': w,
                    '总当量': m['总当量成本']} for g, v, m, d, c, w in single]},
          open(H + '/模拟.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s/模拟.json' % H)
