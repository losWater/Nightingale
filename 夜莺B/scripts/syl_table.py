# -*- coding: utf-8 -*-
"""音节过堂表：python syl_table.py ji [最低频万]  —— 按 B 根集算首/末根，按首根分堆。"""
import sys,os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from b_roots import *
from collections import defaultdict
syl=sys.argv[1]; MIN=float(sys.argv[2])*10000 if len(sys.argv)>2 else 10000
chars=sorted({c for c,v in r.items() for f,cd in v if cd[:2]==syl and f>=MIN},key=lambda c:-reading_freq[(c,syl)])
two_preferred=rules.get('two_code_overrides',{}).get(str(syl))
two_code=two_preferred if two_preferred in {c for c,v in r.items() for f,cd in v if cd[:2]==syl} else (chars[0] if chars else None)
if two_code and two_code not in chars: chars.insert(0,two_code)
elif two_code in chars: chars.remove(two_code); chars.insert(0,two_code)
piles=defaultdict(list)
for c in chars[1:]:
    h,hv=head(c); t,tv=tail(c)
    g=glyph(c); struct=('独体' if not g or g['type']!='compound' else g['operator']+''.join(name(o) for o in g['operandList'] if o))
    piles[h].append((c,t,struct,hv,tv))
order=sorted(piles,key=lambda h:-len(piles[h]))
print(f"== {syl}：{len(chars)} 字（≥{int(MIN//10000)}万）；二简已排除：{two_code or '—'}；剩余 {len(piles)} 个首根堆，每堆仅1个三码位，≥2 标 ⚠")
for h in order:
    bychar={row[0]:row for row in piles[h]}
    ordered=short_order(syl,h,list(bychar))
    L=[bychar[c] for c in ordered]; piles[h]=L
    preferred=rules.get('short_code_overrides',{}).get(str(syl),{}).get(str(h))
    mark='⚠' if len(L)>=2 else ' '
    print(f"{mark} [{h}] ×{len(L)}: "+'  '.join(
        f"{'★' if c==preferred else ''}{c}{reading_freq[(c,syl)]//10000}(末{t})" for c,t,s,hv,tv in L))
print("\n结构明细：")
if two_code:
    h,hv=head(two_code); t,tv=tail(two_code)
    seq=' '.join(name(x) for x in FORMAL_SPLITS.get(two_code,[]))
    print(f"  [二简] {two_code}({reading_freq.get((two_code,syl),0)//10000}) | 首{h} 末{t}" + (f" | 序列 {seq}" if seq else ''))
for h in order:
    for c,t,s,hv,tv in piles[h]:
        via='' if hv==c or hv=='笔画' else f" via{name(hv)}"
        seq=' '.join(name(x) for x in FORMAL_SPLITS.get(c,[]))
        detail=f" | 序列 {seq}" if seq else ''
        print(f"  {c}({reading_freq[(c,syl)]//10000}) {s} | 首{h}{via} 末{t}{detail}")
