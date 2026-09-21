# -*- coding: utf-8 -*-
"""把审计报出的每一条摆开，人工判读是真错还是误伤（2026-09-21）。只读。

审计只给「拆分 ≠ 部件拼接」这个信号，信号本身不等于错误。常见的合理不一致有：
  · 根集本来就跨部件边界（某个根同时吃掉两个部件的笔画）；
  · 简繁字形差异（繁体部件在简体字里本就不同形）；
  · 部件在表里的拆法是历史裁定，与字形库的结构划分角度不同。
所以这里逐条打印：部件的期望拆分、字的实际拆分、两者的差在哪，
并标出首末根是否会变（会变才涉及改码）。
"""
import io, sys, os, csv, json, re, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
d = json.load(open(H + '/审计结果.json', encoding='utf-8'))
table = {}
for p in (W + '/55_拆分继承核验/当前完整拆分表.txt', W + '/112_扩展字继承/夜莺2.0扩展字拆分表.txt'):
    for r in csv.DictReader(open(p, encoding='utf-8-sig'), delimiter='\t'):
        table[r['汉字']] = r['完整拆分'].split(' ＋ ')
q = open(W + '/65_群友离线工具包/夜莺2.0离线工具包/拆分查询.html', encoding='utf-8-sig').read()
D = json.JSONDecoder().raw_decode(q[re.search(r'\bconst D\s*=\s*', q).end():])[0]
KEY = {}
for c, x in D.items():
    for r in x.get('根', []): KEY[r['根']] = r['键']
freq = {}
for l in open(W + '/30_形码盒子1.0复测/默认字频.txt', encoding='utf-8-sig'):
    p = l.rstrip('\r\n').split('\t')
    if len(p) == 2 and p[1].isdigit(): freq[p[0]] = int(p[1])
det = {x['字']: x for x in d['明细']}
def show(title, groups):
    print('\n' + '═' * 88); print(title); print('═' * 88)
    for op, ys in groups:
        exp_op = table.get(op)
        print('\n【部件 %s】表里%s  牵连 %d 字' % (op, ('拆作 ' + ' ＋ '.join(exp_op)) if exp_op else '不在拆分表（由字形递归得出）', len(ys)))
        for y in sorted(ys, key=lambda t: (-freq.get(t, 0), t))[:8]:
            e = det.get(y)
            if not e: continue
            a, x = e['实际'], e['期望']
            chg = (a[0], a[-1]) != (x[0], x[-1])
            print('   %s%s 实际 %s' % (y, '(字频%s)' % freq[y] if y in freq else '', ' ＋ '.join(a)))
            print('   %s 期望 %s   首末根%s' % (' ' * (1 + (6 if y in freq else 0)), ' ＋ '.join(x),
                                            '会变 → 涉及改码' if chg else '不变'))
        if len(ys) > 8: print('   …另 %d 字' % (len(ys) - 8))
show('系统性（同一部件牵连多字）', sorted(d['系统性'].items(), key=lambda kv: -len(kv[1])))
show('个案（只牵连一个字）', sorted(d['个案'].items(), key=lambda kv: kv[0]))
