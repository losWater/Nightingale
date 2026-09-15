from pathlib import Path
import json,runpy,html
from collections import defaultdict
P=Path(__file__).resolve().parent
n={'__file__':str(P/'review_three_codes.py')};exec((P/'review_three_codes.py').read_text(encoding='utf-8').split('ledgerpath=')[0],n)
raw=json.loads((P/'yong-yue-jiao-raw.json').read_text(encoding='utf-8'));base=n['BASE'];G=n['grouping']()
def merged(x):return G('月') if x=='用' else G(x)
rows={}
for mode in ['use','joint']:
 rows[mode]=dict(base)
 for c,seq in raw[mode].items():
  if seq!=raw['base'][c]:
   assert c not in n['RB']['manual'],'需人工边界复核 '+c
   assert base[c]==raw['base'][c],'维护拆分存在差异 '+c
   rows[mode][c]=seq
results=[n['audit']('ADD','加用并月，保留角',base,rows['use'],G,merged,'试算'),n['audit']('DEL','在用归月基础上删角',rows['use'],rows['joint'],merged,merged,'试算'),n['audit']('JOINT','加用归月并删角',base,rows['joint'],G,merged,'候选')]
source=P.parents[2]/'releases/v1.0/01_正式码表/夜莺1.0字词表_码前.txt'
codes=defaultdict(list);rank=defaultdict(int)
for line in source.read_text(encoding='utf-8-sig').splitlines():
 bits=line.split('\t')
 if len(bits)!=2:continue
 code,c=bits;rank[code]+=1
 if len(c)==1 and rank[code]==1:codes[c].append(code)
double=runpy.run_path(str(P.parent/'03_字音频率审计/rebuild.py'))['double_code']
risk=[]
for g in results[-1]['新增首根候选组']:
 s=g['音节'];cs=[]
 for x in g['字']:
  old=[code for code in codes[x['字']] if len(code)==3 and code[:2]==double(s)]
  if old:cs.append({'字':x['字'],'原三简':old,'原组':G(base[x['字']][0])})
 if len({x['原组'] for x in cs})>1:risk.append({'音节':s,'字':cs})
changed=[{'字':c,'原拆分':n['show'](base[c]),'新拆分':n['show'](seq)} for c,seq in rows['joint'].items() if seq!=base[c]]
payload={'方案':'新增用归月及青字底组；删角，角改⺈＋用','当前背景':n['DEFAULT'],'步骤':results,'改变拆分':changed,'1.0实际三简直接风险':risk,'来源码表':str(source)}
(P/'用归月删角联合试算.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
md=['# 新增用归月、删角联合试算','','月原组包含月、青字底（⺝）。本次仅试算，未实装。独立根组减少1，根形数量一增一减。','']
for r in results:
 md+=[f"## {r['方案']}",f"新增首根字对 {r['新增首根字对']}；三简位置净减少 {r['三码位净减少']}；新增完整重码 {r['新增完整重码']}，消除 {r['消除完整重码']}。",'新增完整重码：'+str(r['新增完整明细'])]
md+=['','## 1.0实际三简直接风险',json.dumps(risk,ensure_ascii=False),'','## 新增首根竞争']
for g in results[-1]['新增首根候选组']:md.append(g['音节']+'：'+'；'.join(x['字']+'〔'+x['拆分']+'〕' for x in g['字']))
md+=['','## 拆分变化']+[x['字']+'：'+x['原拆分']+' → '+x['新拆分'] for x in changed]
(P/'用归月删角联合试算.md').write_text('\n'.join(md),encoding='utf-8')
ledger=P.parent/'02_改动台账/改动台账.json';d=json.loads(ledger.read_text(encoding='utf-8-sig'))
assert not any(e['id']=='COMBO-001' for e in d['entries'])
d['entries'].append({'id':'COMBO-001','title':'新增用归月并删角联合试算','decision':'候选','implementation':'未实装','proposal':{'kind':'add_merge_delete_candidate','add_root':'用','host':'月','remove_root':'角','replacement':['⺈','用']},'dependencies':{'roots':['用','月','青字底','角','⺈'],'characters':[x['字'] for x in changed]},'evaluations':[],'history':[{'date':'2026-09-12','event':'按用户要求联合试算，结果见04_逐根删除评估/用归月删角联合试算.json；等待裁定。'}]})
ledger.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
runpy.run_path(str(ledger.parent/'maintain.py'))['render'](d)
for r in results:
 print(r['方案'],r['新增首根字对'],r['三码位净减少'],r['新增完整重码'],r['新增完整明细'])
print('CHANGED',len(changed),'RISK',risk)
for g in results[-1]['新增首根候选组']:print(g['音节'],[(x['字'],x['拆分']) for x in g['字']])
