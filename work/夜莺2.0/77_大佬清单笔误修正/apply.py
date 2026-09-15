# -*- coding: utf-8 -*-
"""修正外部建议清单三处笔误的照抄实装。
whw→whe(望)；ufd 对深属多余，归还神；qmd→qma(浅)，潜退全码 qmab。
三处笔误当初各抢走一个字的自然三简：枉 whw、神 ufd、黔 qmd，本次归还。
实现：各码位候选1 的单字替换，词条与序号不动。"""
import io,sys,json,hashlib,shutil,datetime,collections
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
B='E:/夜莺2.0/work/夜莺2.0'
SUB={'whe':('忘','望'),'whw':('望','枉'),'ufd':('深','神'),'qma':('潜','浅'),'qmd':('浅','黔')}
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
    miss=[c for c in SUB if hit[c]!=1]
    assert not miss,('命中异常',rel,{c:hit[c] for c in miss})
    assert len(out)==len(lines)
    data=nl.join(out+([tail] if tail is not None else [])).encode(enc)
    open(src,'wb').write(data)
    res.append({'文件':rel,'替换行数':sum(hit.values()),'行数':len(lines),
                '新sha256':hashlib.sha256(data).hexdigest()})
    print('%-46s 替换 %d 行  %s' % (rel.split('/')[-1],sum(hit.values()),res[-1]['新sha256'][:16]))
wl=B+'/54_补删鹿旁保留羊南心四起点试跑/二简人工复核/第二十一批_简码任选项定稿/无理码.json'
shutil.copy2(wl,'实装前备份/无理码.json')
old=json.load(open(wl,encoding='utf-8-sig')); new={k:v for k,v in old.items() if k=='lqq'}
open(wl,'w',encoding='utf-8-sig').write(json.dumps(new,ensure_ascii=False,indent=2))
print('\n无理码登记 %s → %s' % (old,new))
json.dump({'时间':datetime.datetime.now().isoformat(timespec='seconds'),
  '来源':'外部建议清单三处笔误（用户裁定）：whw应为whe、ufd对深属多余、qmd应为qma',
  '码位替换':{k:{'前':v[0],'后':v[1]} for k,v in SUB.items()},
  '归还自然三简':{'枉':'whw','神':'ufd','黔':'qmd'},'退到全码':{'忘':'whev','潜':'qmab'},
  '无理码登记':{'前':old,'后':new},'文件':res},
  open('实装报告.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
