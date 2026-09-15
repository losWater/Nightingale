from pathlib import Path
from collections import Counter
import json,yaml
O=Path(__file__).resolve().parent
manifest=json.loads((O/'manifest.json').read_text(encoding='utf-8'))
bounds=[0,300,500,1500,3000,6000,8454]
data=[]
lines=['# 试跑三码效率分段明细','', '≤三码包括一简、二简、三简；不是严格小于三码。排名按本轮已分配字音频率降序，因此计数单位是字音项，不是去重汉字。多音字可能分属不同区间。','', '区间互不重叠；每段字频覆盖率的分母是该段已分配字频。频次未分配的身份保留计数，不据此视为现实零频。四码含首选与选重，另列四码选重项。补出的三简入口不重复计数。','']
for result in manifest['results']:
 card=next(c for c in manifest['cards'] if c['id']==result['id'])
 es=yaml.safe_load((O/card['elements']).read_text(encoding='utf-8'))
 rows=[l.split('\t') for l in (Path(result['output'])/'code.txt').read_text(encoding='utf-8').splitlines()]
 items=[]
 for e,r in zip(es,rows):
  assert e['词']==r[0]
  if len(e['词'])==1:items.append({'字':e['词'],'拼音':e['拼音'],'频率':e['频率'],'码长':len(r[3]),'首选':int(r[4])==0})
 assert len(items)==8454
 def stat(lo,hi):
  part=items[lo:hi];cnt=Counter(r['码长'] for r in part);den=sum(r['频率'] for r in part)
  short=[r for r in part if r['码长']<=3 and r['首选']]
  return {'区间':f'{lo+1}–{hi}','字音项数':len(part),'一简':cnt[1],'二简':cnt[2],'三简':cnt[3],'四码':cnt[4],'四码选重':sum(r['码长']==4 and not r['首选'] for r in part),'≤三码首选项数':len(short),'≤三码首选数量占比':len(short)/len(part),'段内≤三码首选字频覆盖':sum(r['频率'] for r in short)/den if den else None,'已分配频率合计':den}
 segments=[stat(lo,hi) for lo,hi in zip(bounds,bounds[1:])];total=stat(0,8454)
 assert sum(r['≤三码首选项数'] for r in segments)==result['final']['三码及以内首选项数']
 assert abs(total['段内≤三码首选字频覆盖']-result['final']['三码及以内首选字频覆盖'])<1e-12
 cumulative=[stat(0,n) for n in [300,500,1500,1674,3000,3527,6000,8454]]
 data.append({'起点':result['id'],'分段':segments,'总计':total,'累计层':cumulative})
 lines += [f'## {result["id"]}','', '|区间|一简|二简|三简|四码|其中四码选重|≤三码首选项数|数量占比|段内字频覆盖|','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for r in segments+[dict(total,区间='总计')]:
  rate='无已分配频率' if r['段内≤三码首选字频覆盖'] is None else f"{r['段内≤三码首选字频覆盖']:.2%}"
  lines.append(f"|{r['区间']}|{r['一简']}|{r['二简']}|{r['三简']}|{r['四码']}|{r['四码选重']}|{r['≤三码首选项数']}/{r['字音项数']}|{r['≤三码首选数量占比']:.2%}|{rate}|")
 lines+=['']
lines+=['累计前1674、3527等优化层数据另存于三码效率分段明细.json，不能与上述互斥区间直接相加。']
(O/'三码效率分段明细.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(O/'三码效率分段明细.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=O/'试跑结果.md';text=p.read_text(encoding='utf-8')
link='\n详细数量与互斥分段见 [三码效率分段明细](三码效率分段明细.md)。包含各段一二三四码数量、≤三码首选数量及段内字频覆盖率。\n'
if link not in text:p.write_text(text+link,encoding='utf-8')
print(json.dumps(next(r for r in data if r['起点']=='02_perturbed'),ensure_ascii=False))
