# -*- coding: utf-8 -*-
"""字词冲突二维分档表。
字：有简码则按简码算（故只有无简码的字能与四码词同码）；词：只计四码词，简词不计。"""
import io,sys,json,collections,datetime
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
B='E:/夜莺2.0/work/夜莺2.0'
TOL={'jv','jvb','jvn','jvo','xv','yvl','yvz','yvc','yvo','eh'}
crank={e['字']:e['字频'] for e in json.load(open(B+'/59_单字当量排行/单字当量排行.json',encoding='utf-8'))}
wrank={}
for line in open(B+'/08_词库与词频重建/综合词表_审计候选.jsonl',encoding='utf-8'):
    try: d=json.loads(line)
    except Exception: continue
    w=d.get('词')
    if w and d.get('综合排名') and w not in wrank: wrank[w]=d['综合排名']
codes=collections.defaultdict(set); order=collections.defaultdict(list)
for line in open(B+'/64_加入鲸凉鹤简词/夜莺2.0含简词字词表_普通格式.txt',encoding='utf-8-sig'):
    p=line.rstrip('\n').rstrip('\r').split('\t')
    if len(p)<2 or not p[1].isalpha(): continue
    codes[p[0]].add(p[1]); order[p[1]].append(p[0])
real=lambda w:{c for c in codes[w] if c not in TOL}
# 字的实际入口码
entry={}
for w,cs in codes.items():
    if len(w)!=1: continue
    r=real(w); s=[c for c in r if len(c)<4]
    entry[w]=(min(s,key=len) if s else min((c for c in r if len(c)>=4),default=None), bool(s))
# 四码词按码归集
w4=collections.defaultdict(list)
for w,cs in codes.items():
    if len(w)<2: continue
    for c in cs:
        if len(c)==4: w4[c].append(w)
# 冲突：无简码的字，其全码 == 某四码词的码
CB=[(500,'前500'),(1500,'前1500'),(3500,'前3500'),(5000,'前5000'),(10**9,'全部')]
WB=[(2000,'前2000'),(5000,'前5000'),(10000,'前1万'),(20000,'前2万'),(60000,'前6万'),(10**9,'全部')]
conf=[]
for w,(code,hasshort) in entry.items():
    if hasshort or not code or len(code)!=4: continue
    for word in w4.get(code,()):
        conf.append({'码':code,'字':w,'字频':crank.get(w,99999),
                     '词':word,'词频':wrank.get(word,10**9),'词长':len(word),
                     '现首选':order[code][0],'候选':order[code]})
M=[[0]*len(WB) for _ in CB]
for x in conf:
    for i,(ct,_) in enumerate(CB):
        if x['字频']>ct: continue
        for j,(wt,_) in enumerate(WB):
            if x['词频']<=wt: M[i][j]+=1
print('字词冲突二维累计表（单元格＝冲突对数）\n')
print('%-8s'%'' + ''.join('%9s'%n for _,n in WB))
for i,(_,cn) in enumerate(CB):
    print('%-8s'%cn + ''.join('%9d'%M[i][j] for j in range(len(WB))))
print('\n冲突对总数 %d，涉及码位 %d 个，涉及字 %d 个，涉及词 %d 个'
      % (len(conf),len({x['码'] for x in conf}),len({x['字'] for x in conf}),len({x['词'] for x in conf})))
print('无词频记录的词参与的冲突：%d 对' % sum(1 for x in conf if x['词频']>=10**9))
print('\n按词长：',dict(collections.Counter(x['词长'] for x in conf)))
print('现首选是词的冲突对：%d ／ 是字的：%d'
      % (sum(1 for x in conf if len(x['现首选'])>1),sum(1 for x in conf if len(x['现首选'])==1)))
json.dump({'时间':datetime.datetime.now().isoformat(timespec='seconds'),
  '口径':'字有简码则按简码算（故仅无简码字入表）；词仅计四码词；容错码不算简码',
  '字分档':[n for _,n in CB],'词分档':[n for _,n in WB],'矩阵':M,
  '冲突':sorted(conf,key=lambda x:(x['字频'],x['词频']))},
  open('二维表.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
