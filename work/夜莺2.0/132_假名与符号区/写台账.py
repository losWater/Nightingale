# -*- coding: utf-8 -*-
"""把 o 区方案（假名 + 符号）写成台账行，交给 00_维护/apply_ledger.py 落到两张主表。
单字符的条目两表都进（符号也要能在单字表模块里打出来）；多字符的（拗音 きゃ、m³、m̀）只进字词表。
已有码位（ofdw）上夜莺原有的条目不动，新增的排在后面。可重复运行：台账里已有 P0003 就不再追加。"""
import io, sys, os, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H); L = W + '/00_维护/实战问题机器参数.tsv'
plan = json.load(open(H + '/o区方案.json', encoding='utf-8'))
items = []      # (码, 内容) 按落位顺序
for x in plan['假名']:
    items += [(x['平假名码'], t) for t in x['平假名']] + [(x['片假名码'], t) for t in x['片假名']]
for key in ('日语标点', '数字序号', '拼音声调', 'of成组符号'):
    for x in plan[key]: items += [(x['码'], t) for t in x['候选']]
for x in plan['ot特殊符号']: items += [(x['码'], t) for t in x['候选']]
assert all('\t' not in t and '\n' not in t for _, t in items), '内容里有制表符或换行'
dup = [k for k, v in collections.Counter(items).items() if v > 1]
assert not dup, '同一码位有重复条目：%s' % dup[:5]
# 现有主表，跳过已存在的
ex = {'单字表': set(), '字词表': set()}
for name in ex:
    for l in open(W + '/00_维护/主表/夜莺2.0%s.txt' % name, encoding='utf-8'):
        t, c = l.rstrip('\n').split('\t'); ex[name].add((t, c))
s = open(L, encoding='utf-8-sig').read()
if 'P0003-' in s: sys.exit('台账里已有 P0003，不重复写。要重来先从台账里删掉这些行。')
SRC = 'o 区：or 平假名 / ob 片假名（训令式，小字与拗音挂对应假名）、orb 日语标点、old olx 罗马数字、oxu 圆圈数字、op 拼音四声、ot 特殊符号、of 成组符号。方案表见 132_假名与符号区'
rows = []; n = 0; skip = 0
for code, text in items:
    for tab in (('单字表', '字词表') if len(text) == 1 else ('字词表',)):
        if (text, code) in ex[tab]: skip += 1; continue
        n += 1
        rows.append(['P0003-%04d' % n, SRC if n == 1 else '同上', '待处理', tab, '新增', '', '', code, text, '',
                     'o 区符号，排该码位最后', '', '', '', ''])
open(L, 'w', encoding='utf-8-sig', newline='').write(s + ''.join('\t'.join(r) + '\n' for r in rows))
byc = collections.Counter(c for c, _ in items)
print('方案 %d 个码位、%d 条；写入台账 %d 行（单字表 %d，字词表 %d），已存在跳过 %d'
      % (len(byc), len(items), len(rows), sum(1 for r in rows if r[3] == '单字表'), sum(1 for r in rows if r[3] == '字词表'), skip))
print('多字符条目（只进字词表）%d 个：%s' % (sum(1 for _, t in items if len(t) > 1), '、'.join(t for _, t in items if len(t) > 1)[:80]))
