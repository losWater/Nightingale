# -*- coding: utf-8 -*-
"""把 o 区方案写成第三张主表 00_维护/主表/夜莺2.0符号表.txt（2026-09-17 你定的三表架构）。

  原本（不发布）：单字表、字词表、符号表
  发布：综合表 = 字词表 + 符号表（+ 快符）；普通单字表 = 单字表 + 符号表（含多字符的符号）

符号表格式与另两张主表一致：符号<Tab>编码，UTF-8 无 BOM、LF，同码的先后即候选次序。
符号不进两张主表，所以 Rime 的整句词典、反查、辅助码天然不受污染。已存在则拒绝覆盖。"""
import io, sys, os, json, hashlib, datetime, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H); M = W + '/00_维护/主表/夜莺2.0符号表.txt'
plan = json.load(open(H + '/o区方案.json', encoding='utf-8'))
items = []
for x in plan['假名']:
    items += [(x['平假名码'], t) for t in x['平假名']] + [(x['片假名码'], t) for t in x['片假名']]
for key in ('日语标点', '数字序号', '拼音声调', 'of成组符号'):
    for x in plan[key]: items += [(x['码'], t) for t in x['候选']]
for x in plan['ot特殊符号']: items += [(x['码'], t) for t in x['候选']]
assert all('\t' not in t and '\n' not in t and t for _, t in items)
dup = [k for k, v in collections.Counter(items).items() if v > 1]; assert not dup, dup[:5]
# 与另两张主表不能撞条目；撞码位的（ofdw）在导出时排在原有条目之后
old = {}
for name in ('单字表', '字词表'):
    for l in open(W + '/00_维护/主表/夜莺2.0%s.txt' % name, encoding='utf-8'):
        t, c = l.rstrip('\n').split('\t'); old[(t, c)] = name
same = [(t, c, old[(t, c)]) for c, t in items if (t, c) in old]
assert not same, '与主表条目重复：%s' % same[:5]
byc = collections.defaultdict(list)
for c, t in items: byc[c].append(t)
body = ''.join('%s\t%s\n' % (t, c) for c in sorted(byc) for t in byc[c])
assert not os.path.exists(M), '符号表已存在，拒绝覆盖：' + M
open(M, 'wb').write(body.encode('utf-8'))
clash = sorted(set(c for c in byc if any(cc == c for _, cc in old)))
json.dump({'时间': datetime.datetime.now().isoformat(timespec='seconds'), '条目': len(items), '码位': len(byc),
           'sha256': hashlib.sha256(body.encode('utf-8')).hexdigest(),
           '与主表同码位': clash, '来源': '132_假名与符号区/o区方案.json',
           '说明': 'o 区：or 平假名 / ob 片假名（训令式）、orb 日语标点、old olx 罗马数字、oxu 圆圈数字、op 拼音四声、ot 特殊符号、of 成组符号。'},
          open(W + '/00_维护/主表/符号表说明.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('符号表 %d 条、%d 个码位 → %s' % (len(items), len(byc), M))
print('与主表同码位（导出时排在原有条目之后）：%s' % ('、'.join(clash) or '无'))
