# -*- coding: utf-8 -*-
"""估算：按排除规则筛 work/夜莺2.0，看入库体积与仍偏大的目录/文件。规则与 sync.py 共用（rules.py）。"""
import io, sys, os, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rules import walk_included, MAX_FILE
W = 'E:/夜莺2.0/work/夜莺2.0'
MB = lambda b: '%.1f' % (b / 1048576)
inc, exc = walk_included(W)
ti = sum(s for p, s in inc); te = sum(s for p, s, why in exc)
print('入库 %s MB / %d 文件；排除 %s MB / %d 文件' % (MB(ti), len(inc), MB(te), len(exc)))
why = collections.Counter(); whys = collections.Counter()
for p, s, w in exc: why[w] += 1; whys[w] += s
print('\n排除原因:')
for w, n in why.most_common(): print('  %9s MB %6d  %s' % (MB(whys[w]), n, w))
top = collections.Counter(); topn = collections.Counter()
for p, s in inc: d = p.split('/')[0]; top[d] += s; topn[d] += 1
print('\n入库后仍最大的 25 个目录:')
for d, s in top.most_common(25): print('  %9s MB %6d  %s' % (MB(s), topn[d], d))
print('\n入库文件 >20MB:')
for p, s in sorted(inc, key=lambda t: -t[1]):
    if s > 20 * 1048576: print('  %9s MB  %s' % (MB(s), p))
