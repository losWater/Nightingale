from pathlib import Path
import json,runpy,difflib
P=Path(__file__).resolve().parent
source=(P/'evaluate_candidate_additions.py').read_text(encoding='utf-8-sig')
exec(source[:source.index('res=[];states={};groups={}')])
r=json.loads((P/'xian-lan-delete-raw.json').read_text(encoding='utf-8'))
assert r['base']==json.loads((P/'guo-li-current-raw.json').read_text(encoding='utf-8'))['joint']
results=[]
for key,title,id in [('xian','删贤字头','DEL-030'),('lan','删览字头','DEL-031'),('both','两根同时删除','COMBO-006')]:
 rows=dict(base)
 for ch,seq in r[key].items():
  if seq==r['base'][ch]:continue
  old=r['base'][ch];updated=list(base[ch])
  for tag,i,j,u,v in reversed(difflib.SequenceMatcher(None,old,seq,autojunk=False).get_opcodes()):
   if tag=='equal':continue
   assert updated[i:j]==old[i:j],(ch,old,updated,seq)
   updated[i:j]=seq[u:v]
  rows[ch]=updated
 replacements={}
 if key in ['xian','both']:replacements[n['rid']('贤字头')]=['丨','丨','又']
 if key in ['lan','both']:replacements[n['rid']('览字头')]=['丨','丨',n['rid']('卧人'),'丶']
 rows={ch:[x for t in seq for x in replacements.get(t,[t])] for ch,seq in rows.items()}
 assert not any(t in replacements for seq in rows.values() for t in seq)
 a=audit(title,base,rows,G,G);a['id']=id
 a['完整重码详情']=[{'音节':s,'字1':x,'字2':y,'拆分1':n['show'](rows[x]),'拆分2':n['show'](rows[y]),'分音频次1':n['freq'].get((s,x),0),'分音频次2':n['freq'].get((s,y),0)} for s,x,y in a['新增完整明细']]
 results.append(a)
 print(title,'changed',len(a['拆分变化']),'H',a['新增首根字对'],'S',a['三码位净减少'],'F',a['新增完整重码'],'V1',a['1.0三简风险'])
 print('FULL',a['完整重码详情'])
(P/'贤览字头删除试算.json').write_text(json.dumps({'说明':'基于四组锚定归并确认后的141组；人旁暂时合组，禾木分开。仅试算。','结果':results},ensure_ascii=False,indent=2),encoding='utf-8')
md=['# 贤字头、览字头删除试算','','四组锚定归并确认后141组背景，仅试算。']
for a in results:
 md+=['','## '+a['方案'],'',str({k:a[k] for k in ['新增首根字对','三码位净减少','新增完整重码','1.0三简风险']}),'','| 字 | 原拆分 | 新拆分 |','|---|---|---|']
 md+=['| '+x['字']+' | '+x['原拆分']+' | '+x['新拆分']+' |' for x in a['拆分变化']]
 md+=['','完整重码明细：'+str(a['完整重码详情'])]
(P/'贤览字头删除试算.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
