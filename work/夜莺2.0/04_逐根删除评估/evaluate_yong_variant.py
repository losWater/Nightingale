from pathlib import Path
import json,runpy
P=Path(__file__).resolve().parent
n={'__file__':str(P/'review_three_codes.py')};exec((P/'review_three_codes.py').read_text(encoding='utf-8').split('ledgerpath=')[0],n)
raw=json.loads((P/'yong-yue-jiao-raw.json').read_text(encoding='utf-8'));v=json.loads((P/'yong-variant-raw.json').read_text(encoding='utf-8'))
assert v['joint']==raw['joint']
base=n['BASE'];before=dict(base);after=dict(base)
n['INV']['\ue08c']={'display':'甬字底'}
for target,src in [(before,v['joint']),(after,v['variant'])]:
 for c,seq in src.items():
  if seq!=raw['base'][c]:
   assert c not in n['RB']['manual'] and base[c]==raw['base'][c]
   target[c]=seq
G=n['grouping']()
def pre(x):return G('月') if x=='用' else G(x)
def post(x):return G('月') if x in ['用','\ue08c'] else G(x)
r=n['audit']('VARIANT','甬字底归入用月组',before,after,pre,post,'候选')
total=n['audit']('TOTAL','用与甬字底归月并删角',base,after,G,post,'候选')
changed=[{'字':c,'原拆分':n['show'](before[c]),'新拆分':n['show'](seq)} for c,seq in after.items() if seq!=before[c]]
data={'部件':'甬字底','Chai内部标识':'U+E08C（私用区，不是通用汉字码点）','新增影响':r,'累计方案影响':total,'变化':changed}
(P/'甬字底归用月试算.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
md=['# 甬字底归入用月组试算','','甬字底是Chai现有部件，与用的外框笔形不同；本方案新增为用的归并根，不另开独立组。以新增用归月、删角的候选为前提。',f"新增影响：首根字对{r['新增首根字对']}，三简位置净减少{r['三码位净减少']}，新增完整重码{r['新增完整重码']}。",'新增完整明细：'+str(r['新增完整明细']),f"累计：新增首根字对{total['新增首根字对']}，新增完整重码{total['新增完整重码']}。"]
md += [x['字']+'：'+x['原拆分']+' → '+x['新拆分'] for x in changed]
(P/'甬字底归用月试算.md').write_text('\n\n'.join(md),encoding='utf-8')
f=P.parent/'02_改动台账/改动台账.json';d=json.loads(f.read_text(encoding='utf-8-sig'))
id='COMBO-002'
if not any(e['id']==id for e in d['entries']):d['entries'].append({'id':id,'title':'甬字底归用月组','decision':'候选','implementation':'未实装','proposal':{'kind':'add_variant_candidate','root':'甬字底','host':'用','group':['用','甬字底','月','青字底'],'description':'以前项新增用归月并删角为前提，额外识别Chai甬字底部件，作为用的归并根同组。'},'dependencies':{'roots':['用','甬字底','月','青字底','角'],'characters':[x['字'] for x in changed]},'evaluations':[],'history':[{'date':'2026-09-12','event':'按用户要求试算；结果见04_逐根删除评估/甬字底归用月试算.json，待裁定。'}]})
f.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');runpy.run_path(str(f.parent/'maintain.py'))['render'](d)
print('DELTA',r['新增首根字对'],r['三码位净减少'],r['新增完整重码'],r['新增完整明细'])
print('TOTAL',total['新增首根字对'],total['新增完整重码'],total['新增完整明细'])
print('CHANGED',len(changed));print(changed)
