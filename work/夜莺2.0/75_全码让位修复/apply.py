# -*- coding: utf-8 -*-
"""全码位字对字出简让全修复。
规则：全码位上，已有更短码（同读音前缀）的字让位，排到无简码字之后；让位是降序，不是移除。
本批两处：jxpy 夹让郏；yjsp 焉让嫣、嬿。"""
import io,sys,os,json,hashlib,shutil,datetime
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
B='E:/夜莺2.0/work/夜莺2.0'
TARGET={'jxpy':(['夹','郏','精心培养'],['郏','夹','精心培养']),
        'yjsp':(['焉','嫣','嬿'],        ['嫣','嬿','焉'])}
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
    if f=='plain':   return w+'\t'+c
    if f=='code1st': return c+'\t'+w
    if f=='shouxin': return c+'='+str(i)+','+w
    if f=='sogou':   return c+','+str(i)+'='+w
res=[]
for rel,enc,fmt in FILES:
    src=B+'/'+rel
    shutil.copy2(src,'实装前备份/'+rel.replace('/','__'))
    txt=open(src,'rb').read().decode(enc)
    nl='\r\n' if '\r\n' in txt else '\n'
    lines=txt.split(nl); tail=lines.pop() if lines and lines[-1]=='' else None
    out=[]; i=0; done={}
    while i<len(lines):
        c,w=parse(lines[i],fmt)
        if c in TARGET and c not in done:
            j=i
            blk=[]
            while j<len(lines):
                c2,w2=parse(lines[j],fmt)
                if c2!=c: break
                blk.append(w2); j+=1
            before,after=TARGET[c]
            assert blk==before,('码位成员或次序与预期不符',rel,c,blk)
            out.extend(emit(c,w2,k+1,fmt) for k,w2 in enumerate(after))
            done[c]=True; i=j; continue
        out.append(lines[i]); i+=1
    assert set(done)==set(TARGET),('未全部命中',rel,sorted(done))
    assert len(out)==len(lines),'行数变化'
    data=nl.join(out+([tail] if tail is not None else [])).encode(enc)
    open(src,'wb').write(data)
    res.append({'文件':rel,'新sha256':hashlib.sha256(data).hexdigest(),'行数':len(lines)})
    print('%-46s OK  %s' % (rel.split('/')[-1],res[-1]['新sha256'][:16]))
json.dump({'时间':datetime.datetime.now().isoformat(timespec='seconds'),
           '规则':'全码位上已有更短同读音码的字让位，排到无简码字之后；让位为降序非移除',
           '改动':{k:{'前':v[0],'后':v[1]} for k,v in TARGET.items()},'文件':res},
          open('实装报告.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print('\n完成 %d 个码位' % len(TARGET))
