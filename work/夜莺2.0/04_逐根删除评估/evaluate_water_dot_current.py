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

r=evaluate('MERGE-032','氵冫归点',[('MERGE-032','氵归点','点','氵'),('MERGE-032','冫归点','点','冫')])
r['说明']='当前138组基线（已含耒归横），氵冫与点整组合并；水氺永保持独立，不加入八丷㡀；尚未裁定。'
r['根族']={name:[v['display'] for v in n['I']['inventory'] if G(v['id'])==G(n['rid'](name))] for name in ['氵','冫','点']}
(P/'氵冫归点最新试算.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
for k in ['根族','新增首根字对','消除首根字对','三码位净减少','新增完整重码','消除完整重码','新增完整详情','1.0三简风险','试算根组数','新增首根明细']:print(k,r[k])
md=['# 氵冫归点最新试算','',r['说明'],'',str({k:r[k] for k in ['根族','新增首根字对','三码位净减少','新增完整重码','1.0三简风险','试算根组数']}),'','新增完整重码：'+str(r['新增完整详情']),'','新增首根冲突：'+str(r['新增首根明细'])]
(P/'氵冫归点最新试算.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
