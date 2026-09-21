# -*- coding: utf-8 -*-
"""部件一致性审计：按字形包含关系查拆分是否自洽（2026-09-21）。只读。

140 只能查「登记过」的规则，曲当初没登记所以漏网。这版换依据：
`repos/webchai/.../repertoire.json.deflate` 给出每个字的字形结构，
compound 条目直接有 operandList，例如 蛐 = ⿰(虫, 曲)、澧 = ⿰(氵, 豊)、豊 = ⿱(曲, 豆)。

**判据：一个字的拆分，应当等于它各部件拆分的拼接。**
    期望(Y) = 期望(部件1) ＋ 期望(部件2) ＋ …
    部件若在拆分表里就用表里的，不在就继续往下拆（递归），拆不动就放弃这个字。
曲那次正是 蛐 = 虫 + 曲，期望 [虫,囗,横,丨,丨]，实际却是 [虫,由,丨]。

防误伤（本审计的重点，宁可漏报不可错报）：
  ① 字形不唯一（ambiguous 或多个 glyph）的字跳过——字形本身就有分歧，谈不上对错；
  ② 已登记的人工规则涉及的字全部排除：交叉借笔、字架规则、历史结构裁决，
     这些本来就是「有意不按部件边界拆」；
  ③ 只在**全部部件都能算出期望**时才比对，有一个算不出就跳过；
  ④ 结果按「期望与实际的根数是否相同」分档，并按涉及字数聚合到部件上——
     同一个部件牵连多个字，才是真正的系统性错拆；只牵连一个字的多半是个案，单列。
自测：`--selftest` 用 139 的修复前备份跑，必须报出含曲的那批字，否则判据无效。
"""
import io, sys, os, csv, json, zlib, yaml, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
R = os.path.dirname(W) + '/重开工程/02_规范拆分'
REP = 'E:/夜莺2.0/repos/webchai/packages/hanzi-chai/src/data/repertoire.json.deflate'
SELFTEST = '--selftest' in sys.argv[1:]
LIVE = [W + '/55_拆分继承核验/当前完整拆分表.txt', W + '/112_扩展字继承/夜莺2.0扩展字拆分表.txt']
BAK = [W + '/139_曲根拆分订正/备份/20260921195750_通用规范_当前完整拆分表.txt',
       W + '/139_曲根拆分订正/备份/20260921195750_扩展字_夜莺2.0扩展字拆分表.txt']
table = {}
for p in (BAK if SELFTEST else LIVE):
    for r in csv.DictReader(open(p, encoding='utf-8-sig'), delimiter='\t'):
        table[r['汉字']] = r['完整拆分'].split(' ＋ ')
print('拆分表 %d 字%s' % (len(table), '（修复前备份，自测）' if SELFTEST else ''))
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
print('字形库 %d 条，可用结构 %d 条，字形不唯一跳过 %d 条' % (len(rep), len(COMP), len(AMBIG)))
EXCL = set()
for fn, key in (('传播式整字结构覆写_待验收.yaml', 'propagating_structural_overrides'),
                ('正式字架规则.yaml', 'guarded_rewrites'), ('正式历史结构裁决规则.yaml', 'guarded_rewrites')):
    p = R + '/' + fn
    if not os.path.exists(p): continue
    d = yaml.safe_load(open(p, encoding='utf-8')) or {}
    for ch, v in (d.get(key) or {}).items():
        EXCL.add(ch)
        if isinstance(v, dict):
            for k in ('verified_hits', 'expected_family_examples'):
                for x in (v.get(k) or []): EXCL.add(x)
    for ch, fr in (d.get('frames') or {}).items():
        EXCL.add(ch)
        for x in (fr.get('examples') or {}): EXCL.add(x)
print('已登记规则涉及、予以排除 %d 个字\n' % len(EXCL))
memo = {}
def expect(ch, depth=0):
    """部件的期望拆分：表里有就用表里的；否则按字形继续往下拆；拆不动返回 None。"""
    if depth > 8: return None
    if ch in memo: return memo[ch]
    memo[ch] = None                       # 防环
    if ch in table: memo[ch] = list(table[ch]); return memo[ch]
    ops = COMP.get(ch)
    if not ops or ch in AMBIG: return None
    out = []
    for o in ops:
        s = expect(o, depth + 1)
        if s is None: return None
        out += s
    memo[ch] = out
    return out
mismatch = []
for y, ops in COMP.items():
    if y not in table or y in EXCL or y in AMBIG: continue
    exp = []
    ok = True
    for o in ops:
        s = expect(o) if o != y else None
        if s is None: ok = False; break
        exp += s
    if not ok or not exp: continue
    if table[y] == exp: continue
    mismatch.append((y, ops, table[y], exp))
print('可比对的字 %d 个中，拆分与部件拼接不一致 %d 个' % (
      sum(1 for y, ops in COMP.items() if y in table and y not in EXCL and y not in AMBIG), len(mismatch)))
# 聚合到「肇事部件」：期望里有、实际里没有的那段
def blame(actual, exp):
    out = []
    for o, ops_, a, e in ():
        pass
    return out
byop = collections.defaultdict(list)
for y, ops, act, exp in mismatch:
    for o in ops:
        s = expect(o)
        if s and len(s) >= 2 and not any(act[i:i + len(s)] == s for i in range(len(act) - len(s) + 1)):
            byop[o].append(y)
print('\n' + '═' * 84)
print('按部件聚合：同一部件在多个字里没被一致地拆（牵连 ≥2 字，系统性问题）')
print('═' * 84)
multi = {o: ys for o, ys in byop.items() if len(ys) >= 2}
for o, ys in sorted(multi.items(), key=lambda kv: -len(kv[1])):
    e = expect(o)
    print('  部件 %-4s 应拆作 %-30s %2d 字：%s'
          % (o, ' ＋ '.join(e), len(ys), '、'.join(sorted(ys)[:20]) + ('…' if len(ys) > 20 else '')))
if not multi: print('  （无）')
single = {o: ys for o, ys in byop.items() if len(ys) == 1}
print('\n只牵连一个字的部件 %d 个（多为个案，另列）：%s'
      % (len(single), '、'.join('%s→%s' % (o, ys[0]) for o, ys in list(single.items())[:24])))
json.dump({'模式': '自测' if SELFTEST else '现行', '不一致字数': len(mismatch),
           '系统性': {o: ys for o, ys in multi.items()}, '个案': {o: ys for o, ys in single.items()},
           '明细': [{'字': y, '部件': ops, '实际': a, '期望': e} for y, ops, a, e in mismatch]},
          open(H + ('/自测.json' if SELFTEST else '/审计结果.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n→ %s' % (H + ('/自测.json' if SELFTEST else '/审计结果.json')))
