# -*- coding: utf-8 -*-
"""按夜莺B当前根集计算每字首根/末根（沿 chai 首链/末链找第一个在根集中的部件，否则落到首/末笔画类）。"""
import io,sys,json,zlib,yaml
from collections import defaultdict
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
B='D:/nightingale/'
rep=json.loads(zlib.decompress(open(B+'repos/webchai/packages/hanzi-chai/src/data/repertoire.json.deflate','rb').read()))
db={(chr(e['unicode']) if e.get('unicode') else e.get('name')):e for e in rep}
byname={e.get('name'):k for k,e in db.items() if e.get('name')}
r=json.load(open(B+'work/readings.json',encoding='utf-8')); freq={c:v[0][0] for c,v in r.items()}
cfg=yaml.safe_load(open(B+'夜莺B/work/根集.yaml',encoding='utf-8'))
def resolve(x): return byname.get(x,x)
HOST={}
for root,atts in cfg['roots'].items():
    HOST[resolve(root)]=root
    for a in atts: HOST[resolve(a)]=root
for root,atts in cfg.get('anchors',{}).items():
    for a in atts: HOST[resolve(a)]=a   # 锚定根自己是根（键位随宿主），这里保留自身名
def name(k): return db.get(k,{}).get('name',k) if len(k)==1 and 0xE000<=ord(k)<=0xF8FF else k
def glyph(k):
    e=db.get(k); gs=e['glyphs'] if e else []
    for g in gs:
        if g['type']=='compound' and 'G' in g.get('tags',[]): return g
    for g in gs:
        if g['type']=='compound': return g
    return gs[0] if gs else None
def cls(f):
    if f in ('横','提'): return '横'
    if f=='竖': return '竖'
    if f=='撇': return '撇'
    if f in ('点','捺'): return '点'
    return '折'
def strokes(k,d=0):
    e=db.get(k)
    if not e or d>8: return None
    g=glyph(k)
    if not g: return None
    if g['type']=='basic_component': return [s.get('feature') for s in g['strokes']]
    if g['type']=='compound':
        out=[]
        for o in g['operandList']:
            if not o: continue
            s=strokes(o,d+1)
            if s is None: return None
            out+=s
        return out
    if g['type']=='derived_component':
        src=g.get('source'); base=strokes(src,d+1) if src else None
        if base is None: return None
        out=[]; bi=0
        for f in [s.get('feature') for s in g.get('strokes',[])]:
            if f=='reference':
                if bi<len(base): out.append(base[bi]); bi+=1
            else: out.append(f)
        return out or None
    return None
def chain(c,idx):
    """首链(idx=0)/末链(idx=-1)：字→最外层部件→其子部件→…"""
    g=glyph(c); out=[c]
    while g and g['type']=='compound' and len(out)<7:
        ops=[o for o in g['operandList'] if o]
        if not ops: break
        out.append(ops[idx]); g=glyph(ops[idx])
    return out
def root_of(c,idx):
    """沿链找根；返回 (根名, 经由部件)"""
    g=glyph(c); k=c; depth=0
    while depth<8:
        if k in HOST: return HOST[k],k
        g=glyph(k)
        if not g or g['type']!='compound': break
        ops=[o for o in g['operandList'] if o]
        if not ops: break
        k=ops[idx]; depth+=1
    st=strokes(k)
    if st: return cls(st[0] if idx==0 else st[-1]),'笔画'
    return '?','?'
def head(c): return root_of(c,0)
def tail(c): return root_of(c,-1)
if __name__=='__main__':
    top=sorted(r,key=lambda c:-freq[c])
    N=int(sys.argv[1]) if len(sys.argv)>1 else 3500
    same=[];unk=[]
    for c in top[:N]:
        h,hv=head(c); t,tv=tail(c)
        if '?' in (h,t): unk.append(c); continue
        if h==t and HOST.get(c) is None: same.append((c,h,hv,tv))
    print(f"前{N}字中，按B根集首末根相同(abxx)且自身不是根的：{len(same)} 个")
    print(' '.join(f"{c}{freq[c]//10000}[{h}]" for c,h,hv,tv in same))
    print('无法判定:',len(unk),''.join(unk[:40]))
