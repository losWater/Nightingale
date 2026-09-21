# -*- coding: utf-8 -*-
"""二码位只留前 3 个候选，第 4 个起删掉（2026-09-22 你定）。只追加台账，由 apply_ledger 执行。
第 4 个起要按数字键才能选，不如不放；被删的都是二字词，各有四码全码，照样打得出来（已核实 63/63）。"""
import io, sys, os, csv, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
P = W + '/00_维护/实战问题机器参数.tsv'
ci = collections.defaultdict(list); where = collections.defaultdict(list)
for l in open(W + '/00_维护/主表/夜莺2.0字词表.txt', encoding='utf-8'):
    t, c = l.rstrip('\n').split('\t'); ci[c].append(t); where[t].append(c)
drop = [(c, w) for c, v in ci.items() if len(c) == 2 and len(v) > 3 for w in v[3:]]
assert all(len(w) > 1 for _, w in drop), '有单字会被删，停手'
assert all(any(len(x) == 4 for x in where[w]) for _, w in drop), '有词没有四码全码，停手'
old = list(csv.reader(open(P, encoding='utf-8-sig'), delimiter='\t'))
if any(r and r[0].startswith('P0009') for r in old[1:]): sys.exit('P0009 已存在')
with open(P, 'a', encoding='utf-8-sig', newline='') as f:
    wr = csv.writer(f, delimiter='\t', lineterminator='\n')
    for n, (c, w) in enumerate(drop, 1):
        wr.writerow(['P0009-%03d' % n, '二码位只留前三个', '待处理', '字词表', '删除', c, w, '', '', '',
                     '第 4 位起需数字键；该词另有四码全码', '', '', '', ''])
print('已追加 %d 行删除' % len(drop))
