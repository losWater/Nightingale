# -*- coding: utf-8 -*-
"""o 引导符号区删一批（2026-09-22 你定）：逗号、句号、分号、引号，以及快符里已有的符号。按条目文字精确匹配，追加台账。"""
import io, sys, os, re, csv, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
DEL = set('，,。.．；;“”‘’"\'「」『』＂＇')
for l in open(W + '/106_全平台导出/参考模板/快符原表.txt', encoding='utf-8-sig'):
    m = re.fullmatch(r'[a-z]+,\d+=(.+)', l.strip())
    if m: DEL.add(m.group(1))
rows = [tuple(l.rstrip('\n').split('\t')) for l in open(W + '/00_维护/主表/夜莺2.0符号表.txt', encoding='utf-8')]
hit = [(t, c) for t, c in rows if t in DEL]
by = collections.defaultdict(list)
for t, c in hit: by[t].append(c)
print('符号表 %d 条，删 %d 条：' % (len(rows), len(hit)))
for t, cs in by.items(): print('  %s  %s' % (t, ' '.join(cs)))
P = W + '/00_维护/实战问题机器参数.tsv'
old = list(csv.reader(open(P, encoding='utf-8-sig'), delimiter='\t'))
if any(r and r[0].startswith('P0013') for r in old[1:]): sys.exit('P0013 已存在')
with open(P, 'a', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    for n, (t, c) in enumerate(hit, 1):
        w.writerow(['P0013-%03d' % n, 'o符号区删逗号句号分号引号及快符已有', '待处理', '符号表', '删除', c, t, '', '', '', '', '', '', '', ''])
