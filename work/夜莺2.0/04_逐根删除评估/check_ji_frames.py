from pathlib import Path
import runpy,json
P=Path(__file__).resolve().parent
ctx=runpy.run_path(str(P/'current_state.py'));n=ctx['ns'];rows=ctx['rows'];G=ctx['group']
a,b=G('几'),G('匚')
def merged(x):return '几匚' if G(x) in [a,b] else G(x)
r=n['audit']('MERGE-021','几家族与匚框家族同组',rows,rows,G,merged,'候选')
# Actual v1.0 three-code first choices, excluding within-original-group collisions.
code_source=P.parents[2]/'releases/v1.0/01_正式码表/夜莺1.0字词表_码前.txt'
from collections import defaultdict
rank=defaultdict(int);codes=defaultdict(list)
for line in code_source.read_text(encoding='utf-8-sig').splitlines():
 parts=line.split('\t')
 if len(parts)!=2:continue
 code,c=parts;rank[code]+=1
 if len(c)==1 and len(code)==3 and rank[code]==1:codes[c].append(code)
double=runpy.run_path(str(P.parent/'03_字音频率审计/rebuild.py'))['double_code'];risk=[]
for g in r['新增首根候选组']:
 s=g['音节'];out=[]
 for item in g['字']:
  c=item['字'];old=[x for x in codes[c] if x[:2]==double(s)]
  if old:out.append({'字':c,'三简':old,'原组':G(rows[c][0]),'频次':n['freq'][s,c]})
 if len({x['原组'] for x in out})>1:risk.append({'音节':s,'字':out})
data={'范围':'几、周字框⺆、风省⺇、凡；匚、凵、冂、门、巨、勹、匃、贝字框、門。仅根族同组，不加入w键其他根。','背景':'采用current_state.py：含已确认用与甬字底归月、删角、举字底归王丰；人旁合并待定未启用。','评估':r,'1.0三简直接风险':risk}
(P/'几与框家族合并试算.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
md=['# 几家族与框家族合并试算','',data['范围'],data['背景'],f"新增首根字对{r['新增首根字对']}；理论三简位置净减少{r['三码位净减少']}；新增完整重码{r['新增完整重码']}；消除完整重码{r['消除完整重码']}。",'新增完整重码：'+str(r['新增完整明细']),'','## 1.0现有三简直接风险',json.dumps(risk,ensure_ascii=False)]
(P/'几与框家族合并试算.md').write_text('\n\n'.join(md),encoding='utf-8')
f=P.parent/'02_改动台账/改动台账.json';d=json.loads(f.read_text(encoding='utf-8-sig'))
d['entries'].append({'id':'MERGE-021','title':'几家族与匚框家族合并试算','decision':'候选','implementation':'未实装','proposal':{'kind':'merge_root_candidate','root':'几','host':'匚','description':data['范围']},'dependencies':{'roots':['几','周字框','风省','凡','匚','凵','冂','门','巨','勹','匃','见二','門'],'characters':[]},'evaluations':[],'history':[{'date':'2026-09-12','event':'按用户要求联合新基线试算，结果见04_逐根删除评估/几与框家族合并试算.json。'}]})
f.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');runpy.run_path(str(f.parent/'maintain.py'))['render'](d)
print('METRICS',r['新增首根字对'],r['三码位净减少'],r['新增完整重码'],r['新增完整明细']);print('RISK',risk)
