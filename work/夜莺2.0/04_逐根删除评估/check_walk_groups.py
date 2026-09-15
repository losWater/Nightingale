from pathlib import Path
import json,runpy
from collections import defaultdict
P=Path(__file__).resolve().parent
ctx=runpy.run_path(str(P/'current_state.py'));n=ctx['ns'];rows=ctx['rows'];G=ctx['group'];families={k:G(n['rid'](k)) for k in ['足','止','定字底']}
def merged(x):return '走止足定底' if G(x) in families.values() else G(x)
r=n['audit']('MERGE-023','走止足定字底合并',rows,rows,G,merged,'候选')
members={key:[v.get('display',k) for k,v in n['INV'].items() if G(k)==group] for key,group in families.items()}
uses=[{'字':c,'拆分':n['show'](seq)} for c,seq in rows.items() if any(G(t) in families.values() for t in seq)]
codes=defaultdict(list);rank=defaultdict(int)
source=P.parents[2]/'releases/v1.0/01_正式码表/夜莺1.0字词表_码前.txt'
for line in source.read_text(encoding='utf-8-sig').splitlines():
 bits=line.split('\t')
 if len(bits)!=2:continue
 code,c=bits;rank[code]+=1
 if len(c)==1 and len(code)==3 and rank[code]==1:codes[c].append(code)
double=runpy.run_path(str(P.parent/'03_字音频率审计/rebuild.py'))['double_code'];risk=[]
for g in r['新增首根候选组']:
 s=g['音节'];cs=[]
 for x in g['字']:
  c=x['字'];old=[code for code in codes[c] if code[:2]==double(s)]
  if old:cs.append({'字':c,'三简':old,'原组':G(rows[c][0])})
 if len({x['原组'] for x in cs})>1:risk.append({'音节':s,'字':cs})
data={'成员':members,'评估':r,'相关根族使用字':uses,'1.0三简直接风险':risk,'前提':'最新21根已删，含已确认各归并组；人旁四组合并暂计入。'}
(P/'走止足定字底试算.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
md=['# 走止足定字底合并试算','',str(members),data['前提'],f"相关根族使用{len(uses)}字；新增首根冲突{r['新增首根字对']}对，三简位置净减少{r['三码位净减少']}；新增完整重码{r['新增完整重码']}对，消除{r['消除完整重码']}对。",'新增完整明细：'+str(r['新增完整明细']),'1.0实际三简风险：'+str(risk)]
md += [g['音节']+'：'+'、'.join(x['字']+'〔'+x['拆分']+'〕' for x in g['字']) for g in r['新增首根候选组']]
md += ['相关根族用字：'+'、'.join(x['字'] for x in uses)]
(P/'走止足定字底试算.md').write_text('\n\n'.join(md),encoding='utf-8')
f=P.parent/'02_改动台账/改动台账.json';d=json.loads(f.read_text(encoding='utf-8-sig'))
d['entries'].append({'id':'MERGE-023','title':'走止足定字底合并试算','decision':'候选','implementation':'未实装','proposal':{'kind':'merge_root_candidate','roots':['足','止','定字底'],'description':'足（含足旁、走）、止、定字底（含畏下、疋、走下）三个现有根族合并，保留拆分，待裁定。'},'dependencies':{'roots':['足','足旁','走','止','定字底','畏字底带横','疋','走下'],'characters':[x['字'] for x in uses]},'evaluations':[],'history':[{'date':'2026-09-12','event':'按最新21根删除基线试算；见04_逐根删除评估/走止足定字底试算.json。'}]})
f.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');runpy.run_path(str(f.parent/'maintain.py'))['render'](d)
print(members,'USES',len(uses));print('METRICS',r['新增首根字对'],r['三码位净减少'],r['新增完整重码'],r['新增完整明细']);print('RISK',risk);print('USES',uses)
for g in r['新增首根候选组']:print(g['音节'],[(x['字'],x['拆分']) for x in g['字']])
