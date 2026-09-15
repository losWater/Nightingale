from pathlib import Path
import json,runpy,html,hashlib
from collections import defaultdict
P=Path(__file__).resolve().parent
ctx=runpy.run_path(str(P/'current_state.py'));n=ctx['ns'];base=ctx['rows'];G=ctx['group']
raw=json.loads((P/'fourteen-current-raw.json').read_text(encoding='utf-8'));targets=json.loads((P/'review-deletions.json').read_text(encoding='utf-8'))
assert raw['base']==json.loads((P/'yong-variant-raw.json').read_text(encoding='utf-8'))['variant']
raw['JOINT']=json.loads((P/'fourteen-joint-current-raw.json').read_text(encoding='utf-8'))['joint']
ids=[f'DEL-{i:03}' for i in range(3,17)]
codes=defaultdict(list);rank=defaultdict(int)
source=P.parents[2]/'releases/v1.0/01_正式码表/夜莺1.0字词表_码前.txt'
for line in source.read_text(encoding='utf-8-sig').splitlines():
 bits=line.split('\t')
 if len(bits)!=2:continue
 code,c=bits;rank[code]+=1
 if len(c)==1 and len(code)==3 and rank[code]==1:codes[c].append(code)
double=runpy.run_path(str(P.parent/'03_字音频率审计/rebuild.py'))['double_code']
result=[]
for id in ids+['JOINT']:
 selected=ids if id=='JOINT' else [id];rep={targets[k]['id']:targets[k]['replacement'] for k in selected};after=dict(base);manual=[]
 for c,seq in base.items():
  if c in n['RB']['manual']:
   after[c]=[x for t in seq for x in rep.get(t,[t])]
   if after[c]!=seq:manual.append(c)
  elif raw[id][c]!=raw['base'][c]:
   assert seq==raw['base'][c],('维护边界需复核',c)
   after[c]=raw[id][c]
 assert not any(t in rep for seq in after.values() for t in seq)
 title='14根同时删除' if id=='JOINT' else targets[id]['display']
 r=n['audit'](id,title,base,after,G,G,'候选，未确认删除')
 changes=[{'字':c,'原拆分':n['show'](base[c]),'新拆分':n['show'](seq)} for c,seq in after.items() if seq!=base[c]]
 r['拆分变化']=changes;r['变化字数']=len(changes);r['人工边界保留字']=manual
 risk=[]
 for g in r['新增首根候选组']:
  sound=g['音节'];old=[]
  for item in g['字']:
   c=item['字'];short=[code for code in codes[c] if code[:2]==double(sound)]
   if short:old.append({'字':c,'三简':short,'原组':G(base[c][0])})
  if len({x['原组'] for x in old})>1:risk.append({'音节':sound,'原三简字':old})
 r['1.0三简直接风险']=risk
 result.append(r)
notes='最新累计方案：已删秉暴尧俞文交角；含用甬字底归月、举字底归王丰、几族归框族、水氺永分组、兔象鱼龟、兼归争字底等已确认方案；人旁四组合并暂时计入。14根逐项删除时其他13根保留，另算同时删除，结果不可直接相加。全8105字、分音频次按现有审计；1.0三简指正式字词表三码首选。首根同组与完整重码分别统计。暂未重新安排一二简或实际键位。'
out=P.parent/'06_14根最新复核';out.mkdir(exist_ok=True)
data={'说明':notes,'结果':result}
(out/'14根最新复核.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
headers=['方案','变化字数','新增首根字对','三码位净减少','新增完整重码','消除完整重码']
md=['# 14根最新复核','',notes,'','| '+' | '.join(headers)+' |','|'+'---|'*len(headers)]
for r in result:md.append('| '+' | '.join(str(r[k]) for k in headers)+' |')
page='<!doctype html><meta charset="utf-8"><title>14根最新复核</title><style>body{font:16px/1.7 Microsoft YaHei,sans-serif;margin:32px;background:#f5f7fa;color:#233548}table{border-collapse:collapse;background:white}th,td{border:1px solid #ccd6dd;padding:8px 14px}details{margin:16px 0;background:white;padding:12px}summary{cursor:pointer;font-weight:bold}</style><h1>14根最新复核</h1><p>'+html.escape(notes)+'</p><table><tr>'+''.join('<th>'+k+'</th>' for k in headers)+'</tr>'
for r in result:page+='<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in headers)+'</tr>'
page+='</table>'
for r in result:
 lines=[r['方案'],'新增完整重码：'+str(r['新增完整明细']),'1.0三简直接风险：'+str(r['1.0三简直接风险'])]
 lines+=['新增首根竞争 '+g['音节']+'：'+'、'.join(x['字']+'〔'+x['拆分']+'〕' for x in g['字']) for g in r['新增首根候选组']]
 lines += [x['字']+'：'+x['原拆分']+' → '+x['新拆分'] for x in r['拆分变化']]
 md+=['','## '+r['方案'],'']+lines[1:]
 page+='<details><summary>'+html.escape(r['方案'])+'</summary>'+''.join('<p>'+html.escape(x)+'</p>' for x in lines[1:])+'</details>'
(out/'14根最新复核.md').write_text('\n\n'.join(md),encoding='utf-8');(out/'14根最新复核.html').write_text(page,encoding='utf-8')
f=P.parent/'02_改动台账/改动台账.json';d=json.loads(f.read_text(encoding='utf-8-sig'))
for e in d['entries']:
 if e['id'] in ids:e.setdefault('history',[]).append({'date':'2026-09-12','event':'按最新累计基线重算独立删除及14根联合删除，详见06_14根最新复核/14根最新复核.json；维持候选，未授权实装。'})
f.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');runpy.run_path(str(f.parent/'maintain.py'))['render'](d)
(out/'来源指纹.json').write_text(json.dumps({str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [P/'current_state.py',P/'fourteen-current-raw.json',P/'fourteen-joint-current-raw.json',source,f]},ensure_ascii=False,indent=2),encoding='utf-8')
for r in result:print(r['方案'],r['变化字数'],'H',r['新增首根字对'],'slots',r['三码位净减少'],'FULL',r['新增完整重码'],r['新增完整明细'],'V1',r['1.0三简直接风险'])
