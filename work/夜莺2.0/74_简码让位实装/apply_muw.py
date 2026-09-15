# -*- coding: utf-8 -*-
"""增量：muw 木让位给模（用户追加裁定）。"""
import io,sys,os,json,hashlib,shutil,datetime,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
B='E:/夜莺2.0/work/夜莺2.0'
X,OLD,NEW='muw','木','模'
FILES=[('64_加入鲸凉鹤简词/夜莺2.0含简词字词表_普通格式.txt','utf-8-sig','plain'),
       ('64_加入鲸凉鹤简词/夜莺2.0含简词字词表_码前格式.txt','utf-8-sig','code1st'),
       ('62_无简词字词表导出/夜莺2.0无简词字词表_普通格式.txt','utf-8-sig','plain'),
       ('62_无简词字词表导出/夜莺2.0无简词字词表_码前格式.txt','utf-8-sig','code1st'),
       ('62_无简词字词表导出/夜莺2.0无简词字词表_手心格式.txt','utf-8-sig','shouxin'),
       ('62_无简词字词表导出/夜莺2.0无简词字词表_搜狗.txt','utf-16','sogou')]
def parse(l,f):
    if f=='plain':   p=l.split('\t'); return (p[1],p[0]) if len(p)>=2 else (None,None)
    if f=='code1st': p=l.split('\t'); return (p[0],p[1]) if len(p)>=2 else (None,None)
    if f=='shouxin':
        if '=' in l and ',' in l: c,r=l.split('=',1); n,w=r.split(',',1); return (c,w)
    if f=='sogou':
        if '=' in l and ',' in l: le,w=l.split('=',1); c,n=le.rsplit(',',1); return (c,w)
    return (None,None)
def rb(l,f,new):
    if f=='plain':   p=l.split('\t'); p[0]=new; return '\t'.join(p)
    if f=='code1st': p=l.split('\t'); p[1]=new; return '\t'.join(p)
    if f=='shouxin': c,r=l.split('=',1); n,w=r.split(',',1); return c+'='+n+','+new
    if f=='sogou':   le,w=l.split('=',1); return le+'='+new
    return l
res=[]
for rel,enc,fmt in FILES:
    src=B+'/'+rel
    shutil.copy2(src,'实装前备份_muw/'+rel.replace('/','__'))
    txt=open(src,'rb').read().decode(enc)
    nl='\r\n' if '\r\n' in txt else '\n'
    lines=txt.split(nl); tail=lines.pop() if lines and lines[-1]=='' else None
    hit=0; out=[]
    for l in lines:
        c,w=parse(l,fmt)
        if c==X and w==OLD: hit+=1; out.append(rb(l,fmt,NEW))
        else: out.append(l)
    assert hit==1,('命中数异常',rel,hit)
    assert len(out)==len(lines)
    data=nl.join(out+([tail] if tail is not None else [])).encode(enc)
    open(src,'wb').write(data)
    res.append({'文件':rel,'替换行数':hit,'新sha256':hashlib.sha256(data).hexdigest()})
    print('%-46s 替换 %d 行  %s' % (rel.split('/')[-1],hit,res[-1]['新sha256'][:16]))
p=json.load(open('让位清单.json',encoding='utf-8'))
p['让位'][X]={'占位字':OLD,'接手字':NEW,'追加裁定':'用户追加：模虽主读音mo已有三简mow，但muw仅此一个竞争者，仍予让出'}
p['维持'].pop(X,None)
json.dump(p,open('让位清单.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
r=json.load(open('实装报告.json',encoding='utf-8'))
r['追加muw']={'时间':datetime.datetime.now().isoformat(timespec='seconds'),'文件':res}
r['让位条数']=len(p['让位']); r['维持条数']=len(p['维持'])
json.dump(r,open('实装报告.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print('\n让位 %d 处，维持 %d 处' % (r['让位条数'],r['维持条数']))
