# -*- coding: utf-8 -*-
"""部件一致性审计（收紧版）：只查「本字有权威拆法」的部件（2026-09-21）。只读。

第一版按「拆分 = 部件拼接」比对，报出 243 条，逐条判读后发现大半是误伤：
  · 齒 30 字、達 5 字、樂 4 字——这些部件**不在我们的拆分表里**，
    而牵连的那些字**彼此完全一致**，只是我们的笔顺约定与字形库不同。
    内部一致就不构成错误，不能因为外部数据不同就改。
  · 𣦼 3 字——它本身就是一个字根，字形库把它再拆成 ⺊＋夕＋又，我们不该跟。

真正的错误长什么样：曲、隶、庸 那种——**本字在表里是一种拆法，派生字却用另一种**，
同一个部件在自家表里有两副面孔。这才是内部不一致。

所以收紧为：
  ① 部件 X 必须在拆分表里有条目（有权威人工拆法），否则跳过；
  ② X 的拆法至少 2 个根（单根部件无信息量）；
  ③ X 不是单个字根（是根就不该再拆）；
  ④ 已登记规则涉及的字排除；字形不唯一的字排除；
  ⑤ 结果再分两类：根名属同组的只是叫法差异（不影响编码），单独列出不算错。
自测：`--selftest` 必须报出曲。
"""
import io, sys, os, csv, json, zlib, yaml, re, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
R = os.path.dirname(W) + '/重开工程/02_规范拆分'
REP = 'E:/夜莺2.0/repos/webchai/packages/hanzi-chai/src/data/repertoire.json.deflate'
SELFTEST = '--selftest' in sys.argv[1:]
LIVE = [W + '/55_拆分继承核验/当前完整拆分表.txt', W + '/112_扩展字继承/夜莺2.0扩展字拆分表.txt']
BAK = [W + '/139_曲根拆分订正/备份/20260921195750_通用规范_当前完整拆分表.txt',
       W + '/139_曲根拆分订正/备份/20260921195750_扩展字_夜莺2.0扩展字拆分表.txt']
# 现行拆分以啾啾工具箱为准（55/112 已冻结，2026-09-21）；自测仍用 139 的修复前备份
_s = open(W + '/65_群友离线工具包/夜莺啾啾工具箱.html', encoding='utf-8-sig').read()
_v = json.JSONDecoder().raw_decode(_s[re.search(r'\b(?:const|let) views\s*=\s*', _s).end():])[0]['query']
D = json.JSONDecoder().raw_decode(_v[re.search(r'\bconst D\s*=\s*', _v).end():])[0]
table = {}
if SELFTEST:
    for p in BAK:
        for r in csv.DictReader(open(p, encoding='utf-8-sig'), delimiter='\t'):
            table[r['汉字']] = r['完整拆分'].split(' ＋ ')
else:
    table = {c: r['新拆'].split(' ＋ ') for c, r in D.items()}
KEY = {}; GRP = {}
for c, x in D.items():
    for r in x.get('根', []): KEY[r['根']] = r['键']; GRP[r['根']] = r['组']
ROOTS = set(KEY)
freq = {}
for l in open(W + '/30_形码盒子1.0复测/默认字频.txt', encoding='utf-8-sig'):
    p = l.rstrip('\r\n').split('\t')
    if len(p) == 2 and p[1].isdigit(): freq[p[0]] = int(p[1])
rep = json.loads(zlib.decompress(open(REP, 'rb').read()))
COMP = {}; AMBIG = set()
for e in rep:
    if not isinstance(e, dict) or 'unicode' not in e: continue
    ch = chr(e['unicode']); gs = e.get('glyphs') or []
    if e.get('ambiguous') or len(gs) != 1: AMBIG.add(ch); continue
    g = gs[0]
    if g.get('type') in ('compound', 'spliced_component') and g.get('operandList'):
        ops = [x for x in g['operandList'] if x]
        if len(ops) >= 2: COMP[ch] = ops
# 排除集只收「本来就不按部件边界拆」的两类：交叉借笔（传播式覆写）与字架重组（frames）。
# guarded_rewrites 不排除——那只是普通的序列裁定，族里本来就该跟着。
# 2026-09-21 教训：隶、庸 的规则登记的是 Chai 的错形式，而族里的字用的是**第三种**旧形式，
# 140 按登记的错形式搜不到，141 又因「已登记」把它们排除，两边都漏。
EXCL = set()
for fn, key in (('传播式整字结构覆写_待验收.yaml', 'propagating_structural_overrides'),):
    p = R + '/' + fn
    if not os.path.exists(p): continue
    d = yaml.safe_load(open(p, encoding='utf-8')) or {}
    for ch, v in (d.get(key) or {}).items():
        EXCL.add(ch)
        if isinstance(v, dict):
            for k in ('verified_hits', 'expected_family_examples'):
                for x in (v.get(k) or []): EXCL.add(x)
for fn in ('正式字架规则.yaml',):
    p = R + '/' + fn
    if not os.path.exists(p): continue
    d = yaml.safe_load(open(p, encoding='utf-8')) or {}
    for ch, fr in (d.get('frames') or {}).items():
        EXCL.add(ch)
        for x in (fr.get('examples') or {}): EXCL.add(x)
print('拆分表 %d 字%s；字形结构 %d 条；已登记排除 %d 字'
      % (len(table), '（修复前备份，自测）' if SELFTEST else '', len(COMP), len(EXCL)))
def contains(ch, x, depth=0):
    """ch 的字形里是否（递归）含部件 x。"""
    if depth > 6: return False
    ops = COMP.get(ch)
    if not ops: return False
    if x in ops: return True
    return any(contains(o, x, depth + 1) for o in ops if o != ch)
def sub(seq, s):
    n = len(s); return any(seq[i:i + n] == s for i in range(len(seq) - n + 1))
# 候选部件：在拆分表里、拆法≥2根、本身不是字根
CAND = [x for x, s in table.items() if len(s) >= 2 and x not in ROOTS and x not in AMBIG and x not in EXCL]
print('候选部件 %d 个（本字在表里、拆法≥2根、本身不是字根）\n' % len(CAND))
bad = collections.defaultdict(list)
for y, ops in COMP.items():
    if y not in table or y in EXCL or y in AMBIG: continue
    sy = table[y]
    # 误伤排除：Y 自身就是一个字根（如 乔、匈），它的拆法是单根，本来就不该再按部件拼
    if len(sy) == 1 and sy[0] in ROOTS: continue
    for x in ops:
        if x == y or x not in table or x in ROOTS or len(table[x]) < 2 or x in EXCL: continue
        if sub(sy, table[x]): continue
        bad[x].append(y)
def same_group(a, b):
    return GRP.get(a) is not None and GRP.get(a) == GRP.get(b)
real = {}; alias = {}
for x, ys in bad.items():
    sx = table[x]
    # 若差异仅是同组根名，归入别名类
    allalias = True
    for y in ys:
        sy = table[y]
        hit = False
        for i in range(len(sy) - len(sx) + 1):
            if all(a == b or same_group(a, b) for a, b in zip(sy[i:i + len(sx)], sx)): hit = True; break
        if not hit: allalias = False; break
    (alias if allalias else real)[x] = ys
print('═' * 86)
print('真不一致：部件本字的拆法，在含它的字里没有被沿用（%d 个部件）' % len(real))
print('═' * 86)
for x, ys in sorted(real.items(), key=lambda kv: -len(kv[1])):
    print('\n【%s】本字拆作 %s   牵连 %d 字' % (x, ' ＋ '.join(table[x]), len(ys)))
    for y in sorted(ys, key=lambda t: (-freq.get(t, 0), t))[:10]:
        sy = table[y]
        print('   %-3s%-10s 实际 %s' % (y, '(字频%d)' % freq[y] if y in freq else '', ' ＋ '.join(sy)))
    if len(ys) > 10: print('   …另 %d 字' % (len(ys) - 10))
print('\n' + '═' * 86)
print('仅根名差异（同组同键，不影响编码，不算错）：%d 个部件' % len(alias))
print('═' * 86)
for x, ys in sorted(alias.items(), key=lambda kv: -len(kv[1])):
    print('  %-3s 本字 %-24s 牵连 %d 字：%s' % (x, ' ＋ '.join(table[x]), len(ys), '、'.join(sorted(ys)[:12])))
json.dump({'模式': '自测' if SELFTEST else '现行',
           '真不一致': {x: ys for x, ys in real.items()}, '根名差异': {x: ys for x, ys in alias.items()}},
          open(H + ('/收紧_自测.json' if SELFTEST else '/收紧_审计结果.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\n→ %s' % (H + ('/收紧_自测.json' if SELFTEST else '/收紧_审计结果.json')))
