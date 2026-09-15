from pathlib import Path
import json,runpy,difflib
P=Path(__file__).resolve().parent
source=(P/'evaluate_candidate_additions.py').read_text(encoding='utf-8-sig')
exec(source[:source.index('res=[];states={};groups={}')])
r=json.loads((P/'final-candidates-raw.json').read_text(encoding='utf-8'));assert r['base']==json.loads((P/'restore-di-raw.json').read_text(encoding='utf-8'))['restore']
rows=dict(base)
for x in '食攴支辰刃亥':n['INV'][x]={'display':x}
for ch,seq in r['all'].items():
 if seq==r['base'][ch]:continue
 old=r['base'][ch];u=list(base[ch])
 for tag,i,j,a,b in reversed(difflib.SequenceMatcher(None,old,seq,autojunk=False).get_opcodes()):
  if tag=='equal':continue
  assert u[i:j]==old[i:j],(ch,u,old,seq)
  u[i:j]=seq[a:b]
 rows[ch]=u
hosts={'食':'饣','攴':'又','支':'又','辰':'氏','刃':'刀'}
def ag(x):
 if x=='亥':return '新增独立根:亥'
 if x in hosts:return G(n['rid'](hosts[x]))
 g=G(x)
 if g==G('皮'):return G('毛')
 if g==G(n['rid']('氵')):return G(n['rid']('点'))
 return g
a=audit('剩余候选联合确认',base,rows,G,ag);a['id']='COMBO-008';a['状态']='已确认'
a['说明']='以此前135组为基线，食饣、攴支又、辰氏、刃刀，亥独立，毛皮锚定，氵冫点合组。人旁合组已确认，付保留；击二山用于本次计算，举字底凵保留备选。'
a['试算根组数']=len({ag(x) for seq in rows.values() for x in seq})
a['完整详情']=[{'音节':s,'字1':x,'字2':y,'拆分1':n['show'](rows[x]),'拆分2':n['show'](rows[y])} for s,x,y in a['新增完整明细']]
(P/'剩余候选联合确认.json').write_text(json.dumps(a,ensure_ascii=False,indent=2),encoding='utf-8');(P/'剩余候选累计拆分.json').write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')
for k in ['试算根组数','新增首根字对','三码位净减少','新增完整重码','消除完整重码','完整详情','1.0三简风险']:print(k,a[k])
print('变化字数',len(a['拆分变化']))
