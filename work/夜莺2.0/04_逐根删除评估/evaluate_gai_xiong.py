from pathlib import Path
import json,runpy,difflib
P=Path(__file__).resolve().parent
source=(P/'evaluate_candidate_additions.py').read_text(encoding='utf-8-sig')
exec(source[:source.index('res=[];states={};groups={}')])
r=json.loads((P/'gai-xiong-raw.json').read_text(encoding='utf-8'));assert r['base']==json.loads((P/'restore-chi-raw.json').read_text(encoding='utf-8'))['restore']
n['INV']['匈']={'display':'匈'}
results=[]
for key,title,id in [('delete','删除匃','DEL-032'),('xiong','保留匃，新增匈归框族','ADD-017')]:
 rows=dict(base)
 for ch,seq in r[key].items():
  if seq==r['base'][ch]:continue
  old=r['base'][ch];updated=list(base[ch])
  for tag,i,j,u,v in reversed(difflib.SequenceMatcher(None,old,seq,autojunk=False).get_opcodes()):
   if tag=='equal':continue
   assert updated[i:j]==old[i:j],(ch,old,updated,seq)
   updated[i:j]=seq[u:v]
  rows[ch]=updated
 if key=='delete':
  rows={ch:[x for t in seq for x in (['勹','人',n['rid']('折')] if t=='匃' else [t])] for ch,seq in rows.items()}
  assert all('匃' not in seq for seq in rows.values())
 ag=(lambda x:G('匃') if x=='匈' else G(x)) if key=='xiong' else G
 a=audit(title,base,rows,G,ag);a['id']=id
 a['完整详情']=[{'音节':s,'字1':x,'字2':y,'拆分1':n['show'](rows[x]),'拆分2':n['show'](rows[y])} for s,x,y in a['新增完整明细']]
 results.append(a)
 for k in ['方案','新增首根字对','三码位净减少','新增完整重码','消除完整重码','完整详情','1.0三简风险','拆分变化']:print(k,a[k])
(P/'匃删除与匈加根对比.json').write_text(json.dumps({'说明':'当前138组背景；两方案独立试算，未裁定。','结果':results},ensure_ascii=False,indent=2),encoding='utf-8')
md=['# 匃删除与匈加根对比','','当前138组背景，两案独立试算。']
for a in results:
 md+=['','## '+a['方案'],'',str({k:a[k] for k in ['新增完整重码','消除完整重码','三码位净减少','1.0三简风险']}),'','| 字 | 原拆分 | 新拆分 |','|---|---|---|']
 md+=['| '+x['字']+' | '+x['原拆分']+' | '+x['新拆分']+' |' for x in a['拆分变化']]
 md+=['','完整重码：'+str(a['完整详情'])]
(P/'匃删除与匈加根对比.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
