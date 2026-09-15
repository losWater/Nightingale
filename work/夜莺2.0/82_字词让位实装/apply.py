# -*- coding: utf-8 -*-
"""字词让位实装（阶段二）。规则见 码表概念与规则.md 第五节：
1 字有简码+四码词→让；2 多词最多让一位；3 字全可让位则整块后移保原字序；
4 有字不能让位则整组不让；5 无简码但字频>5000的字仅让给二字词；
5a 任何字与三字及以上词同码一律不让；6 人工指定码位不动；容错码不算简码。
每个文件按其自身候选块重算次序（62 无简词表词条较少，结果可能与 64 不同）。"""
import io,sys,json,hashlib,shutil,datetime,collections,html
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
B='E:/夜莺2.0/work/夜莺2.0'
TOL={'jv','jvb','jvn','jvo','xv','yvl','yvz','yvc','yvo','eh'}
rank={e['字']:e['字频'] for e in json.load(open(B+'/59_单字当量排行/单字当量排行.json',encoding='utf-8'))}
man=json.load(open(B+'/64_加入鲸凉鹤简词/码位人工指定.json',encoding='utf-8-sig'))
codes=collections.defaultdict(set)
for line in open(B+'/64_加入鲸凉鹤简词/夜莺2.0含简词字词表_普通格式.txt',encoding='utf-8-sig'):
    p=line.rstrip('\n').rstrip('\r').split('\t')
    if len(p)>=2 and p[1].isalpha() and len(p[0])==1: codes[p[0]].add(p[1])
hasS=lambda w:any(len(c)<4 and c not in TOL for c in codes[w])
def target(F,blk):
    ch=[w for w in blk if len(w)==1]; wd=[w for w in blk if len(w)>1]
    if not ch or not wd or len(F)!=4 or F in man: return blk
    w1=wd[0]
    ok=len(w1)==2 and all(hasS(w) or rank.get(w,99999)>5000 for w in ch)
    return (wd[:1]+ch+wd[1:]) if ok else ch+wd
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
res=[];allchg={}
for rel,enc,fmt in FILES:
    src=B+'/'+rel; shutil.copy2(src,'实装前备份/'+rel.replace('/','__'))
    txt=open(src,'rb').read().decode(enc); nl='\r\n' if '\r\n' in txt else '\n'
    lines=txt.split(nl); tail=lines.pop() if lines and lines[-1]=='' else None
    out=[];i=0;chg={}
    while i<len(lines):
        c,w=parse(lines[i],fmt)
        if c is None or len(c)!=4: out.append(lines[i]); i+=1; continue
        j=i;blk=[]
        while j<len(lines):
            c2,w2=parse(lines[j],fmt)
            if c2!=c: break
            blk.append(w2); j+=1
        new=target(c,blk)
        if new!=blk: chg[c]=(blk,new)
        out.extend(emit(c,x,k+1,fmt) if new!=blk else lines[i+k] for k,x in enumerate(new))
        i=j
    assert len(out)==len(lines),'行数变化'
    data=nl.join(out+([tail] if tail is not None else [])).encode(enc)
    open(src,'wb').write(data)
    res.append({'文件':rel,'调整码位':len(chg),'行数':len(lines),'新sha256':hashlib.sha256(data).hexdigest()})
    allchg[rel.split('/')[-1]]=chg
    print('%-46s 调整 %3d 码位  %s' % (rel.split('/')[-1],len(chg),res[-1]['新sha256'][:16]))
main=allchg['夜莺2.0含简词字词表_普通格式.txt']
A={k:v for k,v in main.items() if len(v[1][0])>1}; C={k:v for k,v in main.items() if len(v[1][0])==1}
json.dump({'时间':datetime.datetime.now().isoformat(timespec='seconds'),
  '规则':'见 码表概念与规则.md 第五节（含 5a）','64调整':len(main),'词占首选':len(A),'字整组前移':len(C),
  '变更':{k:{'前':v[0],'后':v[1]} for k,v in sorted(main.items())},'文件':res},
  open('实装报告.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
e=html.escape
p=['<meta charset="utf-8"><title>字词让位实装清单</title><style>body{font:15px/1.7 "Microsoft YaHei";background:#f2f1eb;color:#243a3a;margin:24px}h2{border-left:4px solid #6b9e93;padding-left:10px}table{border-collapse:collapse;width:100%;background:#fbfaf6}td,th{border:1px solid #d7ddd1;padding:5px 8px}th{background:#e6ebe2;text-align:left}code{background:#e9eee6;padding:1px 5px}.o{color:#9a4a3c}.n{color:#2d6b4f;font-weight:600}</style>',
   '<h1>字词让位实装清单（64 含简词表）</h1><p>%s ｜ 共 %d 处 ｜ 已实装</p>'%(datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),len(main))]
for t,d in (('A 二字词占首选（%d）'%len(A),A),('C 字整组前移（%d）'%len(C),C)):
    p.append('<h2>%s</h2><table><tr><th>码</th><th>前</th><th>后</th></tr>'%t)
    for k,(a,b) in sorted(d.items()): p.append('<tr><td><code>%s</code></td><td class="o">%s</td><td class="n">%s</td></tr>'%(e(k),e('、'.join(a)),e('、'.join(b))))
    p.append('</table>')
open('实装清单.html','w',encoding='utf-8').write(''.join(p))
print('\n64 表调整 %d 处 = 二字词占首选 %d + 字整组前移 %d' % (len(main),len(A),len(C)))
