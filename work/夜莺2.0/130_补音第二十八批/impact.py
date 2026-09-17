# -*- coding: utf-8 -*-
"""补音后，凡补音字与词同码的码位，列出最终次序（字词让位规则跑完之后）。"""
import io, sys, os, json, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); W = os.path.dirname(H)
tab = collections.defaultdict(list)
for l in open(W + '/113_扩展字入表/夜莺2.0最终表_普通格式.txt', encoding='utf-8-sig'):
    t, c = l.rstrip('\r\n').split('\t'); tab[c].append(t)
out = []
for i in json.load(open(H + '/补音清单.json', encoding='utf-8')):
    b = tab[i['全码']]
    if len(b) > 1:
        k = b.index(i['字']); behind = [w for w in b[k + 1:] if len(w) > 1]
        out.append('%s %s：%s%s' % (i['字'], i['全码'], '、'.join(b[:6]), '   ← 排在词「%s」前面' % '、'.join(behind[:3]) if behind else ''))
open(H + '/补音后同码位次序.txt', 'w', encoding='utf-8').write('\n'.join(out) + '\n'); print('\n'.join(out))
