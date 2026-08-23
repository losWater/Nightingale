# -*- coding: utf-8 -*-
"""音节过堂表：python syl_table.py ji [最低频万]  —— 按 B 根集算首/末根，按首根分堆。"""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from b_roots import *
from collections import defaultdict
syl=sys.argv[1]; MIN=float(sys.argv[2])*10000 if len(sys.argv)>2 else 10000
chars=sorted({c for c,v in r.items() for f,cd in v if cd[:2]==syl and freq[c]>=MIN},key=lambda c:-freq[c])
piles=defaultdict(list)
for c in chars:
    h,hv=head(c); t,tv=tail(c)
    g=glyph(c); struct=('独体' if not g or g['type']!='compound' else g['operator']+''.join(name(o) for o in g['operandList'] if o))
    piles[h].append((c,t,struct,hv,tv))
order=sorted(piles,key=lambda h:-len(piles[h]))
print(f"== {syl}：{len(chars)} 字（≥{int(MIN//10000)}万），{len(piles)} 个首根堆；堆容量 2（ab+abx），≥3 标 ⚠")
for h in order:
    L=piles[h]; mark='⚠' if len(L)>=3 else ' '
    print(f"{mark} [{h}] ×{len(L)}: "+'  '.join(f"{c}{freq[c]//10000}(末{t})" for c,t,s,hv,tv in L))
print("\n结构明细：")
for h in order:
    for c,t,s,hv,tv in piles[h]:
        via='' if hv==c or hv=='笔画' else f" via{name(hv)}"
        print(f"  {c}({freq[c]//10000}) {s} | 首{h}{via} 末{t}")
