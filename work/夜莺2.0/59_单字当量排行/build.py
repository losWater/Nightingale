from pathlib import Path
import json,collections,html,hashlib
P=Path(__file__).resolve().parent;W=P.parent;T=W/'54_补删鹿旁保留羊南心四起点试跑';F=T/'frozen'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
b=Path(read(T/'二简人工复核/当前裁定基线.json')['目录']);codes=collections.defaultdict(list);bycode=collections.defaultdict(list)
for l in (b/'普通纯单字表.txt').read_text(encoding='utf-8-sig').splitlines():
 c,k=l.split('\t');bycode[k].append(c);codes[c].append(k)
eq={}
for l in (F/'当量表.tsv').read_text(encoding='utf-8').splitlines():
 if '\t' in l:
  k,v=l.split('\t')
  if len(k)==2:eq[k]=float(v)
pron=collections.defaultdict(list)
for r in read(F/'字音基准.json'):pron[r['字']].append(r)
splits={r['字']:r for r in read(W/'55_拆分继承核验/全部拆分对照.json')};freq={r['字']:r['新排名'] for r in read(W/'32_多来源字频重建/试验整字频率.json')['字表']}
def calc(c,k):
 pos=bycode[k].index(c)+1;seq=k+'='*((pos-1)//3)+[' ',';',"'"][(pos-1)%3];parts=[{'键对':seq[i:i+2].replace(' ','␣'),'成本':eq[seq[i:i+2]]} for i in range(len(seq)-1)];total=sum(x['成本'] for x in parts)
 return {'码':k,'候选位':pos,'输入':seq.replace(' ','␣'),'键数':len(seq),'当量':total/(len(seq)-1),'总成本':total,'键对':parts}
rows=[]
for c,ks in codes.items():
 main=max(pron[c],key=lambda r:r.get('自然频率',r['频率'])) if pron[c] else None
 available=[k for k in ks if main and (k.startswith(main['音码']) or (len(k)==1 and main['音码'].startswith(k)) or (c=='六' and k=='lqq'))]
 fallback=not available
 if fallback:available=ks
 chosen=min([calc(c,k) for k in available],key=lambda x:(x['键数'],x['候选位'],len(x['码']),x['码']))
 rows.append({'字':c,'读音':main['拼音'] if main else '未标注','字频':freq.get(c,999999),'拆分':splits[c]['新拆'],'入口说明':'未匹配主读前缀，取现有最短入口' if fallback else '主读音最短输入','所有编码':[calc(c,k) for k in ks],**chosen})
rows.sort(key=lambda r:(-r['当量'],r['字频'],r['字']))
assert len(rows)==8105 and all(rows[i]['当量']>=rows[i+1]['当量'] for i in range(len(rows)-1))
(P/'单字当量排行.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'单字当量排行.txt').write_text('口径：主读音最短输入；统一键对表；含提交键，不含跨字键对。␣为空格，;次选，单引号三选，=翻页。\n'+''.join(f"{i}. 字：{r['字']}  音：{r['读音']}  输入：{r['输入']}  键均当量：{r['当量']:.5f}  字频：{r['字频']}  拆分：{r['拆分']}\n" for i,r in enumerate(rows,1)),encoding='utf-8-sig')
page=(P/'template.html').read_text(encoding='utf-8').replace('__DATA__',json.dumps(rows,ensure_ascii=False).replace('<','\u003c'))
(P/'单字当量排行.html').write_text(page,encoding='utf-8')
print('覆盖',len(rows),'未匹配主读前缀',sum('未匹配' in r['入口说明'] for r in rows));print([(r['字'],r['输入'],round(r['当量'],4)) for r in rows[:12]])
