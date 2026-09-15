from pathlib import Path
import runpy,json,difflib
P=Path(__file__).resolve().parent
source=(P/'evaluate_candidate_additions.py').read_text(encoding='utf-8-sig')
exec(source[:source.index('res=[];states={};groups={}')])
r=json.loads((P/'sheng-wang-zha-bu-raw.json').read_text(encoding='utf-8'))
assert r['base']==json.loads((P/'wan-qian-raw.json').read_text(encoding='utf-8'))['er']
rows=dict(base)
for x in '生亡乍不':n['INV'][x]={'display':x}
for ch,seq in r['joint'].items():
 if seq==r['base'][ch]:continue
 old=r['base'][ch];updated=list(base[ch])
 for tag,i,j,a,b in reversed(difflib.SequenceMatcher(None,old,seq,autojunk=False).get_opcodes()):
  if tag=='equal':continue
  if updated[i:j]!=old[i:j]:
   assert ch in '嬴瀛羸蠃赢' and '赢字架' in base[ch],('未审查边界',ch)
   break
  updated[i:j]=seq[a:b]
 else:
  rows[ch]=updated
def ag(x):
 if x in ['生','乍']:return '新增独立根:'+x
 if x=='亡':return G(n['rid']('亠'))
 if x=='不':return G(n['rid']('横'))
 return G(x)
a=audit('新增生乍独立、亡归亠、不归横',base,rows,G,ag);a['id']='COMBO-004';a['状态']='已确认'
(P/'生亡乍不联合影响.json').write_text(json.dumps(a,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'生亡乍不累计拆分.json').write_text(json.dumps(rows,ensure_ascii=False),encoding='utf-8')
for k in ['新增首根字对','三码位净减少','新增完整重码','消除完整重码','新增完整明细','1.0三简风险']:print(k,a[k])
print('changed',len(a['拆分变化']))
