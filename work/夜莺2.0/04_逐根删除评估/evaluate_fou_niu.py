from pathlib import Path
import json,runpy,html
from collections import defaultdict
P=Path(__file__).resolve().parent
ctx=runpy.run_path(str(P/'current_state.py'));n=ctx['ns'];base=ctx['rows'];G=ctx['group']
raw=json.loads((P/'fou-niu-wu-ma-raw.json').read_text(encoding='utf-8'));xraw=json.loads((P/'fou-niu-wu-ma-xie-raw.json').read_text(encoding='utf-8'))
assert raw['base']==json.loads((P/'ao-left-raw.json').read_text(encoding='utf-8'))['joint']
n['INV']['午']={'display':'午'};n['INV']['\ue021']={'display':'卸左'}
family={G('缶'),G('牛')}
def grouped(x,horse=True,xie=False):
 if x=='午' or (xie and x=='\ue021') or G(x) in family or (horse and G(x)==G('马')):return '缶牛午马'
 return G(x)
def reconstruct(rawrows,rep):
 out=dict(base)
 for c,seq in rawrows.items():
  if seq==raw['base'][c]:continue
  if c in n['RB']['manual']:
   # Preserve historical manual boundaries; only explicit 击 substitution is allowed.
   out[c]=[x for t in base[c] for x in (rep if t=='击' else [t])]
   assert out[c]==seq,('新增午卸左需人工边界复核',c)
  else:
   assert base[c]==raw['base'][c],('当前边界不符',c)
   out[c]=seq
 assert not any('击' in seq for seq in out.values())
 return out
rank=defaultdict(int);codes=defaultdict(list)
source=P.parents[2]/'releases/v1.0/01_正式码表/夜莺1.0字词表_码前.txt'
for line in source.read_text(encoding='utf-8-sig').splitlines():
 bits=line.split('\t')
 if len(bits)!=2:continue
 code,c=bits;rank[code]+=1
 if len(c)==1 and rank[code]==1:codes[c].append(code)
double=runpy.run_path(str(P.parent/'03_字音频率审计/rebuild.py'))['double_code']
def audit(label,before,after,bg,ag):
 r=n['audit']('COMBO-003',label,before,after,bg,ag,'候选')
 risks=[]
 for g in r['新增首根候选组']:
  s=g['音节'];cs=[]
  for x in g['字']:
   c=x['字'];short=[code for code in codes[c] if len(code)==3 and code[:2]==double(s)]
   if short:cs.append({'字':c,'三简':short,'原组':bg(before[c][0])})
  if len({x['原组'] for x in cs})>1:risks.append({'音节':s,'字':cs})
 r['1.0三简风险']=risks
 r['拆分变化']=[{'字':c,'原拆分':n['show'](before[c]),'新拆分':n['show'](seq)} for c,seq in after.items() if seq!=before[c]]
 return r
res=[];outputs={}
for key,rep in [('ju',[n['rid']('举字底'),'凵']),('er',[n['rid']('二'),'山'])]:
 rows=reconstruct(raw[key],rep);xr=reconstruct(xraw[key],rep);outputs[key]=rows;outputs[key+'_xie']=xr
 tag='击＝'+n['show'](rep)
 nohorse=lambda x:grouped(x,horse=False)
 horse=lambda x:grouped(x)
 withxie=lambda x:grouped(x,xie=True)
 res.append(audit(tag+'；缶牛午同组（无马）',base,rows,G,nohorse))
 res.append(audit(tag+'；马锚定的增量',rows,rows,nohorse,horse))
 res.append(audit(tag+'；缶牛午马累计',base,rows,G,horse))
 res.append(audit(tag+'；卸左加入的增量',rows,xr,horse,withxie))
 res.append(audit(tag+'；含卸左全部累计',base,xr,G,withxie))
notes='前提为最新current_state.py：已删21根，敖左归横等已确认合并已启用；人旁四组暂时计入，走止足定字底合并未启用。第一步击的两种拆法各自试算。第二步新增午；缶、牛家族、午同组，马（含馬）保留主根身份锚定；可选新增卸左归同组。牛家族含牛、牜、制字旁、告字头。报告中的增量与累计不可相加；理论三简净减少负数表示增加。所有方案仅试算，未定案。'
data={'说明':notes,'结果':res}
(P/'缶牛午马与卸左联合试算.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
md=['# 缶牛午马与卸左联合试算','',notes,'','| 方案 | 新增首根对 | 三简位置净减少 | 新增完整重码 | 消除完整重码 |','|---|---:|---:|---:|---:|']
for r in res:md.append('| '+r['方案']+' | '+' | '.join(str(r[k]) for k in ['新增首根字对','三码位净减少','新增完整重码','消除完整重码'])+' |')
for r in res:
 md+=['','## '+r['方案'],'','新增完整重码：'+str(r['新增完整明细']),'1.0三简风险：'+str(r['1.0三简风险'])]
 md += [g['音节']+'：'+'；'.join(x['字']+'〔'+x['拆分']+'〕' for x in g['字']) for g in r['新增首根候选组']]
 md += [x['字']+'：'+x['原拆分']+' → '+x['新拆分'] for x in r['拆分变化']]
(P/'缶牛午马与卸左联合试算.md').write_text('\n\n'.join(md),encoding='utf-8')
f=P.parent/'02_改动台账/改动台账.json';d=json.loads(f.read_text(encoding='utf-8-sig'))
e=next(e for e in d['entries'] if e['id']=='DEL-026');e['selection_status']='两种拆法均保留用于优化比较';e.setdefault('history',[]).append({'date':'2026-09-12','event':'依据用户要求，两种拆法同时纳入本轮缶牛午马及卸左联合评估，暂不选定。'})
d['entries'].append({'id':'COMBO-003','title':'缶牛午同组、马锚定及卸左备选','decision':'候选','implementation':'未实装','proposal':{'kind':'add_merge_anchor_candidate','add_roots':['午'],'merge_roots':['缶','牛','午'],'anchor_main_root':'马','optional_variant':'卸左','description':notes},'dependencies':{'roots':['缶','牛','牜','制字旁','告字头','午','马','馬','卸左','击','举字底','凵','二','山'],'characters':sorted({c for key,r in outputs.items() for c in r if r[c]!=base[c]})},'evaluations':[],'history':[{'date':'2026-09-12','event':'识别午与卸字旁（Chai U+E021），对击的两种拆法分别评估马锚定及卸左加入的增量、累计结果；见04_逐根删除评估/缶牛午马与卸左联合试算.json。'}]})
f.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');runpy.run_path(str(f.parent/'maintain.py'))['render'](d)
for r in res:
 print(r['方案'],'H',r['新增首根字对'],'S',r['三码位净减少'],'F+',r['新增完整重码'],'F-',r['消除完整重码'],r['新增完整明细'],'V1',r['1.0三简风险'])
print('卸左变化',res[3]['拆分变化'])
