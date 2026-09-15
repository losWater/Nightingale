from pathlib import Path
import runpy,json
P=Path(__file__).resolve().parent
source=(P/'evaluate_candidate_additions.py').read_text(encoding='utf-8-sig')
exec(source[:source.index('res=[];states={};groups={}')])
proposals=[('MERGE-025','禾木锚定','禾','木'),('MERGE-026','黑白锚定','黑','白'),('MERGE-027','鸟虫锚定','鸟','虫'),('MERGE-028','大小锚定','大','小'),('MERGE-029','犭与豸整个家族合并','犭','豸')]
def grouped(items):
 parent={}
 def find(x):
  parent.setdefault(x,x)
  if parent[x]!=x:parent[x]=find(parent[x])
  return parent[x]
 for _,_,a,b in items:parent[find(G(n['rid'](b)))]=find(G(n['rid'](a)))
 return lambda x:find(G(x))
def evaluate(id,title,items):
 ag=grouped(items);r=audit(title,base,base,G,ag);r['id']=id
 r['新增完整详情']=[]
 for sound,x,y in r['新增完整明细']:
  r['新增完整详情'].append({'音节':sound,'字1':x,'字2':y,'拆分1':n['show'](base[x]),'拆分2':n['show'](base[y]),'分音频次1':n['freq'].get((sound,x),0),'分音频次2':n['freq'].get((sound,y),0),'待分配频次1':n['pending'].get(x,0),'待分配频次2':n['pending'].get(y,0),'1.0首选码1':codes[x],'1.0首选码2':codes[y]})
 r['新增完整详情'].sort(key=lambda z:-min(z['分音频次1'],z['分音频次2']))
 r['新增完整影响权重']=sum(min(z['分音频次1'],z['分音频次2']) for z in r['新增完整详情'])
 r['试算根组数']=len({ag(t) for seq in base.values() for t in seq})
 return r
res=[evaluate(id,title,[(id,title,a,b)]) for id,title,a,b in proposals]
res.append(evaluate('COMBO-005','五项全部合并累计',proposals))
independent=set(tuple(p) for r in res[:-1] for p in r['新增完整明细'])
res[-1]['仅联合出现的完整冲突']=[p for p in res[-1]['新增完整明细'] if tuple(p) not in independent]
data={'说明':'基于当前145根组（果归里、居已删除、生亡乍不已加入），人旁四组暂时启用。前四项主根锚定，携带各自已有归并家族；犭豸合并含豕、豖。仅试算，未启用。核心8105字；使用同音首末同时相同口径；独立项不可直接相加。','结果':res}
(P/'五组形象锚定试算.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
md=['# 五组形象锚定试算','',data['说明'],'','| 方案 | 新增首根对 | 三简容量减少 | 新增完整重码 | 1.0三简风险组 |','|---|---:|---:|---:|---:|']
for r in res:md.append('| '+r['方案']+' | '+' | '.join(map(str,[r['新增首根字对'],r['三码位净减少'],r['新增完整重码'],len(r['1.0三简风险'])]))+' |')
for r in res:
 md+=['','## '+r['方案'],'','### 新增完整重码','','| 音节 | 字1 | 拆分1 | 字2 | 拆分2 | 分音频次1/2 |','|---|---|---|---|---|---|']
 for z in r['新增完整详情']:md.append('| '+' | '.join(str(z[k]) for k in ['音节','字1','拆分1','字2','拆分2'])+' | '+str(z['分音频次1'])+'/'+str(z['分音频次2'])+' |')
 md+=['','### 1.0已有三简竞争','']
 for z in r['1.0三简风险']:md.append(z['音节']+'：'+'；'.join(x['字']+' '+','.join(x['三简']) for x in z['字']))
 md+=['','### 新增首根冲突','']
 for z in r['新增首根明细']:md.append(z['音节']+'：'+z['字1']+'—'+z['字2'])
(P/'五组形象锚定试算.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
for r in res:
 print(r['方案'],'H',r['新增首根字对'],'S',r['三码位净减少'],'F',r['新增完整重码'],'weight',r['新增完整影响权重'],'V1',len(r['1.0三简风险']))
 print('FULL',r['新增完整明细'])
 print('V1',[(z['音节'],[x['字'] for x in z['字']]) for z in r['1.0三简风险']])
print('联合独有',res[-1]['仅联合出现的完整冲突'])
