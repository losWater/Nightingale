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

import difflib
raw=json.loads((P/'restore-di-raw.json').read_text(encoding='utf-8'));assert raw['base']==json.loads((P/'gai-xiong-raw.json').read_text(encoding='utf-8'))['xiong']
oldbase=base;newbase=dict(base)
for ch,seq in raw['restore'].items():
 if seq==raw['base'][ch]:continue
 old=raw['base'][ch];u=list(base[ch])
 for tag,i,j,a,b in reversed(difflib.SequenceMatcher(None,old,seq,autojunk=False).get_opcodes()):
  if tag=='equal':continue
  assert u[i:j]==old[i:j],(ch,u,old,seq)
  u[i:j]=seq[a:b]
 newbase[ch]=u
r=audit('恢复啇归商',base,newbase,G,G);r['id']='DEL-007恢复';results=[r]
(P/'恢复啇累计拆分.json').write_text(json.dumps(newbase,ensure_ascii=False),encoding='utf-8')
base=newbase
items=[('MERGE-035','厉与十千万锚定','厉','万'),('MERGE-036','里果与田锚定','里','田'),('MERGE-037','儿与子锚定','儿','子')]
for id,title,a,b in items:results.append(evaluate(id,title,[(id,title,a,b)]))
results.append(evaluate('COMBO-007','三项锚定联合',items))
(P/'厉里儿锚定及恢复啇.json').write_text(json.dumps({'说明':'原138组，先恢复啇归商；三个锚定独立及联合试算，未定案。','结果':results},ensure_ascii=False,indent=2),encoding='utf-8')
md=['# 厉、里果、儿锚定及恢复啇','','当前138组；三个锚定以恢复啇后的背景比较。']
for r in results:
 print(r['方案'],'H',r['新增首根字对'],'S',r['三码位净减少'],'F+',r['新增完整重码'],'F-',r['消除完整重码'],'V1',r['1.0三简风险']);print('FULL',r['新增完整明细'])
 md+=['','## '+r['方案'],'',str({k:r[k] for k in ['新增首根字对','三码位净减少','新增完整重码','消除完整重码','1.0三简风险']}),'',str(r.get('新增完整详情',r['新增完整明细']))]
print('恢复啇',results[0]['拆分变化'])
(P/'厉里儿锚定及恢复啇.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
