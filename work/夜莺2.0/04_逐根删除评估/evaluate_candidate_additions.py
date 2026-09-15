from pathlib import Path
import json,runpy,difflib
from collections import defaultdict
P=Path(r'E:\夜莺2.0\work\夜莺2.0\04_逐根删除评估')
ctx=runpy.run_path(str(P/'current_state.py'));n=ctx['ns'];base=ctx['rows'];G=ctx['group']
raw=json.loads((P/'candidate-additions-raw.json').read_text(encoding='utf-8'))
assert raw['base']==json.loads((P/'wan-qian-raw.json').read_text(encoding='utf-8'))['er']
for x in '食攴支辰刃':n['INV'][x]={'display':x}
source=(P/'evaluate_fou_niu.py').read_text(encoding='utf-8')
exec(source[source.index('rank=defaultdict'):source.index('res=[];outputs={}')])
res=[];states={};groups={}
for key,host in [('食','饣'),('攴','又'),('支','又'),('攴支','又'),('辰','氏'),('刃','刀')]:
 rows=dict(base)
 for c,seq in raw[key].items():
  if seq==raw['base'][c]:continue
  old=raw['base'][c]; updated=list(base[c])
  for tag,i,j,a,b in reversed(difflib.SequenceMatcher(None,old,seq,autojunk=False).get_opcodes()):
   if tag=='equal':continue
   assert updated[i:j]==old[i:j],('manual changed span',key,c,updated,old,seq)
   updated[i:j]=seq[a:b]
  rows[c]=updated
 def ag(x,key=key,host=host):return G(n['rid'](host)) if x in key else G(x)
 states[key]=rows;groups[key]=ag
 r=audit(key+'归'+host,base,rows,G,ag);res.append(r)
r=audit('已加攴后再加支',states['攴'],states['攴支'],groups['攴'],groups['攴支']);res.append(r)
(P/'新增根归并试算.json').write_text(json.dumps({'说明':'当前累计裁定背景；人旁四组暂时启用；击默认二山。各项独立试算，不是最终裁定。','结果':res},ensure_ascii=False,indent=2),encoding='utf-8')
for r in res:
 print(r['方案'],'changed',len(r['拆分变化']),'H',r['新增首根字对'],'S',r['三码位净减少'],'F+',r['新增完整重码'],'F-',r['消除完整重码'],r['新增完整明细'],'V1',r['1.0三简风险'])
