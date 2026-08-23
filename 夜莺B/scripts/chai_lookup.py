# -*- coding: utf-8 -*-
"""chai 字形查询：python chai_lookup.py 字或部件名 [...]
输出：结构树（递归展开 PUA 部件）、首链/末链、按夜莺B根集算出的首根/末根、该部件作首/末部件的用户字。"""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from b_roots import *
def show(c,ind=0):
    g=glyph(c)
    if not g: print(' '*ind+f"{name(c)}: 不在 chai 字库"); return
    if g['type']=='compound':
        print(' '*ind+f"{name(c)} = {g['operator']} {[name(o) for o in g['operandList'] if o]}")
        for o in g['operandList']:
            if o and len(o)==1 and 0xE000<=ord(o)<=0xF8FF: show(o,ind+2)
    else:
        st=[s.get('feature') for s in g.get('strokes',[])]
        print(' '*ind+f"{name(c)} = {g['type']} {st if st else ''}")
def users(P):
    return sorted([c for c in freq if P in chain(c,0)[1:] or P in chain(c,-1)[1:]],key=lambda c:-freq[c])
for arg in sys.argv[1:]:
    k=resolve(arg)
    print(f"===== {arg}" + (f" (PUA {hex(ord(k))})" if len(k)==1 and 0xE000<=ord(k)<=0xF8FF else ''))
    show(k)
    print('首链:',' → '.join(name(x) for x in chain(k,0)),' | 末链:',' → '.join(name(x) for x in chain(k,-1)))
    h,hv=head(k); t,tv=tail(k); print(f"B根集 首根={h}{'' if hv in (k,'笔画') else ' via '+name(hv)}  末根={t}{'' if tv in (k,'笔画') else ' via '+name(tv)}")
    u=users(k); print(f"作首/末部件的字 {len(u)}:",' '.join(f"{c}{freq[c]//10000}" for c in u[:30]))
