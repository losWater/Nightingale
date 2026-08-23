# -*- coding: utf-8 -*-
"""合并检查器：python merge_check.py 根1 根2 ... [--name 部件名]  两项都报：三简堆(新增≥3)、全码撞"""
import io,sys,json,zlib
from collections import defaultdict
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
B='D:/nightingale/'
rep=json.loads(zlib.decompress(open(B+'repos/webchai/packages/hanzi-chai/src/data/repertoire.json.deflate','rb').read()))
db={(chr(e['unicode']) if e.get('unicode') else e.get('name')):e for e in rep}
byname={e.get('name'):k for k,e in db.items() if e.get('name')}
r=json.load(open(B+'work/readings.json',encoding='utf-8')); freq={c:v[0][0] for c,v in r.items()}
def name(k): return db.get(k,{}).get('name',k) if len(k)==1 and 0xE000<=ord(k)<=0xF8FF else k
def glyph(k):
    e=db.get(k); gs=e['glyphs'] if e else []
    for g in gs:
        if g['type']=='compound' and 'G' in g.get('tags',[]): return g
    for g in gs:
        if g['type']=='compound': return g
    return gs[0] if gs else None
def chain(c,idx):
    g=glyph(c); out=[c]
    while g and g['type']=='compound' and len(out)<7:
        ops=[o for o in g['operandList'] if o]
        if not ops: break
        out.append(ops[idx]); g=glyph(ops[idx])
    return out
def users(P): return sorted([c for c in freq if P in chain(c,0)[1:] or P in chain(c,-1)[1:] or c==P],key=lambda c:-freq[c])
def resolve(x): return byname.get(x,x)
def report(group):
    G=[resolve(x) for x in group]; S=set(G)
    for P in G:
        u=users(P); print(f"  {name(P)} 首/末 {len(u)}字:",' '.join(f"{c}{freq[c]//10000}" for c in u[:14]))
    # 三简堆：同音节首根∈S（主读音，频≥1万）；只报合并后新出现的≥3堆
    hits=defaultdict(set)
    for c,v in r.items():
        if freq[c]<10000: continue
        s=v[0][1][:2]; hh=[x for x in chain(c,0) if x in S]
        if hh: hits[s].add((c,hh[0]))
    new3=[]; two=0
    for s,cs in hits.items():
        if len({x for _,x in cs})>1:
            per=defaultdict(int)
            for c,x in cs: per[x]+=1
            if len(cs)>=3 and max(per.values())<3: new3.append((s,sorted(cs,key=lambda x:-freq[x[0]])))
            elif len(cs)==2: two+=1
    print(f"  三简：新增≥3堆 {len(new3)} 个，=2堆 {two} 个",' | '.join(s+':'+' '.join(f"{c}{freq[c]//10000}" for c,x in cs) for s,cs in new3[:6]))
    # 全码撞
    hits=defaultdict(list)
    for c,v in r.items():
        for f,cd in v:
            s=cd[:2]; hc=chain(c,0); tc=chain(c,-1)
            hh=[x for x in hc if x in S]; tt=[x for x in tc if x in S]
            if hh: hits[(s,'H',tuple(tc[1:2]))].append((c,hh[0]))
            if tt: hits[(s,'T',tuple(hc[1:2]))].append((c,tt[0]))
    out=[(k,sorted(set(cs),key=lambda x:-freq[x[0]])) for k,cs in hits.items() if len({x for _,x in cs})>1]
    out.sort(key=lambda kc:-freq[kc[1][1][0]]); pain=sum(freq[c] for k,cs in out for c,_ in cs[1:])
    print(f"  全码：撞组 {len(out)}，受害频 {pain//10000}万",' | '.join(k[0]+':'+'/'.join(f"{c}{freq[c]//10000}" for c,x in cs[:3]) for k,cs in out[:6]))
if __name__=='__main__':
    groups=[g.split('+') for g in sys.argv[1:]]
    for g in groups: print('=='," + ".join(g)); report(g)
