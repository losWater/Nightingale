from pathlib import Path
import runpy,json
from collections import defaultdict
P=Path(__file__).resolve().parent
ctx=runpy.run_path(str(P/'current_state.py'));n=ctx['ns'];base=ctx['rows'];G=ctx['group']
codes=defaultdict(list);rank=defaultdict(int)
source=P.parents[2]/'releases/v1.0/01_正式码表/夜莺1.0字词表_码前.txt'
for line in source.read_text(encoding='utf-8-sig').splitlines():
 p=line.split('\t')
 if len(p)!=2:continue
 code,c=p;rank[code]+=1
 if len(c)==1 and rank[code]==1:codes[c].append(code)
double=runpy.run_path(str(P.parent/'03_字音频率审计/rebuild.py'))['double_code']
results=[]
for title,rep in [('举字底＋凵',[n['rid']('举字底'),'凵']),('二＋山',[n['rid']('二'),'山'])]:
 after={c:[x for t in seq for x in (rep if t=='击' else [t])] for c,seq in base.items()}
 r=n['audit']('DEL-026',title,base,after,G,G,'候选')
 r['变化']=[{'字':c,'新拆分':n['show'](seq),'1.0首选码':codes[c]} for c,seq in after.items() if seq!=base[c]]
 risks=[]
 for g in r['新增首根候选组']:
  s=g['音节'];cs=[]
  for x in g['字']:
   c=x['字'];old=[code for code in codes[c] if len(code)==3 and code[:2]==double(s)]
   if old:cs.append({'字':c,'三简':old,'原组':G(base[c][0])})
  if len({x['原组'] for x in cs})>1:risks.append({'音节':s,'字':cs})
 r['1.0三简风险']=risks;results.append(r)
(P/'击两种拆法比较.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
md=['# 击删根两种拆法比较','','按最新累计方案，保留人旁组暂时合并；二＋山为用户指定备选拆法，不是引擎默认结果。']
for r in results:
 md += ['', '## '+r['方案'],f"新增首根冲突{r['新增首根字对']}对；三简位置净减少{r['三码位净减少']}；新增完整重码{r['新增完整重码']}对，消除{r['消除完整重码']}对。",'完整重码：'+str(r['新增完整明细']),'1.0三简风险：'+str(r['1.0三简风险'])]
 md += [g['音节']+'：'+'；'.join(x['字']+'〔'+x['拆分']+'〕' for x in g['字']) for g in r['新增首根候选组']]
 md += [str(x) for x in r['变化']]
(P/'击两种拆法比较.md').write_text('\n\n'.join(md),encoding='utf-8')
f=P.parent/'02_改动台账/改动台账.json';d=json.loads(f.read_text(encoding='utf-8-sig'));e=next(e for e in d['entries'] if e['id']=='DEL-026');e['proposal']['alternatives']=[['举字底','凵'],['二','山']];e.setdefault('history',[]).append({'date':'2026-09-12','event':'新增用户指定二＋山备选拆分；两方案按最新基线比较，见04_逐根删除评估/击两种拆法比较.json。保持候选，不自动选定。'});f.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');runpy.run_path(str(f.parent/'maintain.py'))['render'](d)
for r in results:
 print(r['方案'],'H',r['新增首根字对'],'SLOTS',r['三码位净减少'],'FULL',r['新增完整重码'],r['新增完整明细'],'RISK',r['1.0三简风险']);print(r['变化']);print([(g['音节'],[(x['字'],x['拆分']) for x in g['字']]) for g in r['新增首根候选组']])
