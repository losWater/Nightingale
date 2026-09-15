# -*- coding: utf-8 -*-
"""字词让位修正：居/欲/予/绪 仅有容错码，按“容错码不算简码”属无简码字，
   规则4（有字不能让位则整组不让）→ 单字整组在前，保持原字序，词随后。"""
import io,sys,json,hashlib,shutil,datetime
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
B='E:/夜莺2.0/work/夜莺2.0'
# 码位 -> 期望的单字序（词序保持原样，整体后移）
T={'jubt':['居','局'],'yulx':['欲'],'yuzz':['予'],'xuib':['绪']}
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
def emit(c,w,i,f):
    return {'plain':w+'\t'+c,'code1st':c+'\t'+w,'shouxin':c+'='+str(i)+','+w,'sogou':c+','+str(i)+'='+w}[f]
res=[];changes={}
for rel,enc,fmt in FILES:
    src=B+'/'+rel; shutil.copy2(src,'实装前备份/'+rel.replace('/','__'))
    txt=open(src,'rb').read().decode(enc); nl='\r\n' if '\r\n' in txt else '\n'
    lines=txt.split(nl); tail=lines.pop() if lines and lines[-1]=='' else None
    out=[];i=0;done=set()
    while i<len(lines):
        c,w=parse(lines[i],fmt)
        if c in T and c not in done:
            j=i;blk=[]
            while j<len(lines):
                c2,w2=parse(lines[j],fmt)
                if c2!=c: break
                blk.append(w2); j+=1
            ch=[x for x in blk if len(x)==1]; wd=[x for x in blk if len(x)>1]
            assert ch==T[c],('单字成员/序不符',rel,c,ch,T[c])
            new=ch+wd
            if blk!=new: changes.setdefault(c,(blk,new))
            out.extend(emit(c,x,k+1,fmt) for k,x in enumerate(new)); done.add(c); i=j; continue
        out.append(lines[i]); i+=1
    assert done==set(T),('未全部命中',rel,sorted(set(T)-done))
    assert len(out)==len(lines)
    data=nl.join(out+([tail] if tail is not None else [])).encode(enc)
    open(src,'wb').write(data)
    res.append({'文件':rel,'行数':len(lines),'新sha256':hashlib.sha256(data).hexdigest()})
    print('%-46s OK  %s' % (rel.split('/')[-1],res[-1]['新sha256'][:16]))
for c,(a,b) in changes.items(): print('   %-5s [%s] → [%s]' % (c,'、'.join(a),'、'.join(b)))
json.dump({'时间':datetime.datetime.now().isoformat(timespec='seconds'),
  '规则':'容错码不算简码；有字不能让位则单字整组在前，保持原字序',
  '改动':{c:{'前':a,'后':b} for c,(a,b) in changes.items()},'文件':res},
  open('实装报告.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
