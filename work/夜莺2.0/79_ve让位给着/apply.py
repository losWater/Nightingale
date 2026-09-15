# -*- coding: utf-8 -*-
"""一简+二简兼占修正：这(10) 已有一简 v，二简 ve 让给着(56)。
着的三简 ver 无竞争者，属合法兼占，无连带影响。"""
import io,sys,json,hashlib,shutil,datetime,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
B='E:/夜莺2.0/work/夜莺2.0'
SUB={'ve':('这','着')}
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
res=[]
for rel,enc,fmt in FILES:
    src=B+'/'+rel
    shutil.copy2(src,'实装前备份/'+rel.replace('/','__'))
    txt=open(src,'rb').read().decode(enc)
    nl='\r\n' if '\r\n' in txt else '\n'
    lines=txt.split(nl); tail=lines.pop() if lines and lines[-1]=='' else None
    hit=collections.Counter(); out=[]
    for l in lines:
        c,w=parse(l,fmt)
        if c in SUB and w==SUB[c][0]: hit[c]+=1; out.append(rb(l,fmt,SUB[c][1]))
        else: out.append(l)
    assert all(hit[c]==1 for c in SUB),('命中异常',rel,dict(hit))
    assert len(out)==len(lines)
    data=nl.join(out+([tail] if tail is not None else [])).encode(enc)
    open(src,'wb').write(data)
    res.append({'文件':rel,'替换行数':sum(hit.values()),'行数':len(lines),
                '新sha256':hashlib.sha256(data).hexdigest()})
    print('%-46s 替换 %d 行  %s' % (rel.split('/')[-1],sum(hit.values()),res[-1]['新sha256'][:16]))
json.dump({'时间':datetime.datetime.now().isoformat(timespec='seconds'),
  '规则':'一简/二简兼占：字已有一简时，二简位应让给无一二简的竞争者',
  '改动':{'ve':{'前':'这(10)','后':'着(56)'}},
  '依据':'这已有一简v；ve前缀竞争者23个，最高频为着(56)，着原仅有三简ver',
  '连带核查':'ver/vcr/vor 前缀下除着外无其他无简码字，着的三简兼占合法',
  '文件':res},open('实装报告.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
