from pathlib import Path
import json,html
P=Path(__file__).resolve().parent;T=P.parent/'15_自动晋级赛';read=lambda p:json.loads(p.read_text(encoding='utf-8'))
base=read(T/'最终五名.json');new=[read(p) for p in (P/'jobs').glob('*/round2.json')];assert len(new)==15
records=[]
for label,r in zip('ABCDE',base):
 opt=read(T/'jobs'/r['id']/'optimized.json');items=[{'id':r['id'],'baseline':r['id'],'label':label,'steps':20000,'score':r['score'],'native_score':opt['native_score'],'efficiency':opt['efficiency'],'theory':r['theory'],'benchmark_path':r['benchmark_path']}]+sorted([x for x in new if x['baseline']==r['id']],key=lambda x:x['steps'])
 for item in items:
  b=read(Path(item['benchmark_path']));item['practice_metrics']=b['实战'];records.append(item)
(P/'步数对照结果.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
intro='五个候选各取最初开局，比较总步数2万、3万、5万、10万；不是从2万步结果接着走。除步数外配置逐项校验一致；原生随机流未固定，每档只有一次运行，不能把全部差异归因于步数。第二轮固定语料与草案3计分不变。2万步样本是筛选后的优胜者，存在筛选偏差。'
page=['<!doctype html><meta charset="utf-8"><title>步数对照试跑</title><style>body{font:16px system-ui;background:#f4f7fb;color:#234;padding:26px}td,th{padding:10px;border:1px solid #bfd0df}table{border-collapse:collapse;background:white;margin:20px 0}p{max-width:1200px;line-height:1.8}</style><h1>2万 / 3万 / 5万 / 10万步对照</h1><p>'+intro+'</p>'];md=['# 步数对照结果','',intro]
for label in 'ABCDE':
 page+=['<h2>候选'+label+'</h2><table><tr><th>步数</th><th>原生分↓</th><th>综合分↑</th><th>≤三码首选</th><th>字频覆盖</th><th>单字每字键数↓</th><th>字词每字键数↓</th></tr>'];md+=['','## 候选'+label,'','|步数|原生分↓|综合分↑|≤三码首选|字频覆盖|单字每字键数↓|字词每字键数↓|','|---|---:|---:|---:|---:|---:|---:|']
 for r in [r for r in records if r['label']==label]:
  vals=[r['steps'],f"{r['native_score']:.5f}",f"{r['score']['total']:.4f}",r['efficiency']['三码及以内首选项数'],f"{r['efficiency']['三码及以内首选字频覆盖']:.3%}",f"{r['practice_metrics']['纯单字']['每字击键']:.4f}",f"{r['practice_metrics']['无简词字词']['每字击键']:.4f}"]
  page+=['<tr>'+''.join('<td>'+str(v)+'</td>' for v in vals)+'</tr>'];md+=['|'+'|'.join(map(str,vals))+'|']
 page+=['</table>']
 for title in ['≤三码分段数量','字词增量影响','当量与手感']:
  page+=['<h3>'+title+'</h3><table>']
  items=[r for r in records if r['label']==label]
  page+=['<tr><th>指标</th>'+''.join('<th>'+str(r['steps'])+'</th>' for r in items)+'</tr>']
  if title=='≤三码分段数量':rows=[[items[0]['theory']['分段'][i]['区间']]+[r['theory']['分段'][i]['≤三码首选'] for r in items] for i in range(6)]
  else:
   fields=['字词增量受影响率','字字选重率_单字上屏'] if title=='字词增量影响' else ['键均当量','字均当量','大跨排率','小跨排率','小指占比_不含空格']
   rows=[[mode+' '+field]+[f"{r['practice_metrics'][mode][field]:.6f}" for r in items] for mode in ['纯单字','无简词字词'] for field in fields]
  for row in rows:page+=['<tr>'+''.join('<td>'+str(v)+'</td>' for v in row)+'</tr>']
  page+=['</table>']
(P/'步数对照结果.html').write_text(''.join(page),encoding='utf-8');(P/'步数对照结果.md').write_text('\n'.join(md),encoding='utf-8')
print('COMPLETE')
