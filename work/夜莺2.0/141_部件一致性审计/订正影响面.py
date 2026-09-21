# -*- coding: utf-8 -*-
"""四条订正的完整影响面（2026-09-21，按你定的拆法）。只读。

  庸族  广 ＋ 肀 ＋ 用          —— 你定。注意：慵墉镛鳙 现在跟着庸的旧拆法，也要一起改
  卸左族 𠂉 ＋ 正 → 卸左        —— 啣欫篽蓹衘，字形库确认这五个字的该部件与卸左同源
  年族  𠂉 ＋ 一 ＋ 丨 ＋ 十 → 𠂉 ＋ 横 ＋ 竖 ＋ 横 ＋ 竖   —— 按年的登记规则
  衮族  亠 ＋ 八 ＋ 厶 ＋ 𧘇 → 衣 ＋ 八 ＋ 厶              —— 按衮的拆法
庸是常用字，改了会动码，所以先把每个字的字频与新旧码都摆出来。
"""
import io, sys, os, csv, json, re, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
table = {}
for p in (W + '/55_拆分继承核验/当前完整拆分表.txt', W + '/112_扩展字继承/夜莺2.0扩展字拆分表.txt'):
    for r in csv.DictReader(open(p, encoding='utf-8-sig'), delimiter='\t'): table[r['汉字']] = r['完整拆分']
q = open(W + '/65_群友离线工具包/夜莺2.0离线工具包/拆分查询.html', encoding='utf-8-sig').read()
D = json.JSONDecoder().raw_decode(q[re.search(r'\bconst D\s*=\s*', q).end():])[0]
KEY = {}
for c, x in D.items():
    for r in x.get('根', []): KEY[r['根']] = r['键']
codes = collections.defaultdict(list); zi = collections.defaultdict(list); ci = collections.defaultdict(list)
for l in open(W + '/00_维护/主表/夜莺2.0单字表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t'); codes[t].append(c); zi[c].append(t)
for l in open(W + '/00_维护/主表/夜莺2.0字词表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t'); ci[c].append(t)
freq = {}
for l in open(W + '/30_形码盒子1.0复测/默认字频.txt', encoding='utf-8-sig'):
    p = l.rstrip('\r\n').split('\t')
    if len(p) == 2 and p[1].isdigit(): freq[p[0]] = int(p[1])
RULES = [
    ('庸', '广 ＋ 折 ＋ 二 ＋ 冂 ＋ 举字底', '广 ＋ 肀 ＋ 用'),
    ('庸', '广 ＋ 折 ＋ 二 ＋ ⺝ ＋ 丨', '广 ＋ 肀 ＋ 用'),
    ('卸左', '𠂉 ＋ 正', '卸左'),
    ('年', '𠂉 ＋ 一 ＋ 丨 ＋ 十', '𠂉 ＋ 横 ＋ 竖 ＋ 横 ＋ 竖'),
    ('衮', '亠 ＋ 八 ＋ 厶 ＋ 𧘇', '衣 ＋ 八 ＋ 厶'),
]
new = {}
for why, old, nw in RULES:
    for t, s in table.items():
        if old in s: new[t] = (why, s, (new[t][2] if t in new else s).replace(old, nw))
print('%-3s %-5s %-9s %-34s %-30s %s' % ('字', '族', '字频', '现拆分', '订正后', '编码'))
chg = []
for t in sorted(new, key=lambda x: (-freq.get(x, 0), x)):
    why, old, ns = new[t]
    a = old.split(' ＋ '); b = ns.split(' ＋ ')
    cur = codes.get(t, [])
    full = [c for c in cur if len(c) == 4]
    mark = '不变'
    if (a[0], a[-1]) != (b[0], b[-1]) and full:
        exp = full[0][:2] + KEY.get(b[0], '?') + KEY.get(b[-1], '?')
        mark = '%s → %s' % (','.join(cur), exp)
        chg.append((t, cur, exp, full[0]))
    print('%-3s %-5s %-9s %-34s %-30s %s' % (t, why, freq.get(t, '—'), old[:32], ns[:28], mark))
print('\n需要改码 %d 个：' % len(chg))
for t, cur, exp, full in chg:
    occ_z = zi.get(exp, []); occ_c = ci.get(exp, [])
    print('  %-3s 字频 %-8s %s → %s   新码位现有：单字 %s ／ 字词 %s'
          % (t, freq.get(t, '—'), ','.join(cur), exp, occ_z or '空', occ_c or '空'))
