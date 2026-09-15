from pathlib import Path
import json,runpy,difflib
P=Path(__file__).resolve().parent
source=(P/'evaluate_candidate_additions.py').read_text(encoding='utf-8-sig')
exec(source[:source.index('res=[];states={};groups={}')])
r=json.loads((P/'delete-ju-current-raw.json').read_text(encoding='utf-8'))
assert r['base']==json.loads((P/'sheng-wang-zha-bu-raw.json').read_text(encoding='utf-8'))['joint']
rows=dict(base)
for ch,seq in r['joint'].items():
 if seq==r['base'][ch]:continue
 old=r['base'][ch];updated=list(base[ch])
 for tag,i,j,a,b in reversed(difflib.SequenceMatcher(None,old,seq,autojunk=False).get_opcodes()):
  if tag=='equal':continue
  assert updated[i:j]==old[i:j],(ch,old,updated,seq)
  updated[i:j]=seq[a:b]
 rows[ch]=updated
assert all('居' not in seq for seq in rows.values())
a=audit('删除居，拆尸古',base,rows,G,G);a['id']='DEL-028'
a['新增完整频次']=[{'音节':s,'字1':x,'频次1':n['freq'].get((s,x)),'字2':y,'频次2':n['freq'].get((s,y))} for s,x,y in a['新增完整明细']]
(P/'居删根最新试算.json').write_text(json.dumps(a,ensure_ascii=False,indent=2),encoding='utf-8')
for k in ['新增首根字对','三码位净减少','新增完整重码','消除完整重码','新增完整频次','1.0三简风险','拆分变化']:print(k,a[k])
md=['# 居删根试算','','基于已加入生亡乍不的当前累计方案；仅试算，未裁定。居拆尸古。','','| 字 | 原拆分 | 新拆分 |','|---|---|---|']
md+=['| '+x['字']+' | '+x['原拆分']+' | '+x['新拆分']+' |' for x in a['拆分变化']]
md+=['',str({k:a[k] for k in ['新增首根字对','三码位净减少','新增完整频次','1.0三简风险']})]
(P/'居删根最新试算.md').write_text('\n'.join(md),encoding='utf-8')
