from pathlib import Path
from collections import Counter
import json,yaml
O=Path(__file__).resolve().parent;A=O.parent/'11_多起点试跑'
m=json.loads((O/'manifest.json').read_text(encoding='utf-8'));assert m['status']=='complete'
es={n:yaml.safe_load((A/n).read_text(encoding='utf-8')) for n in ['elements.yaml','elements_ji_ju.yaml']}
old=json.loads((A/'manifest.json').read_text(encoding='utf-8'))
rows=[];details=[]
for r in sorted(m['results'],key=lambda r:r['id']):
 e=es[r['elements']];codes=[l.split('\t') for l in (Path(r['output'])/'code.txt').read_text(encoding='utf-8').splitlines()]
 part=[(item,line) for item,line in zip(e,codes) if len(item['词'])==1]
 total=sum(x['频率'] for x,_ in part)
 bins=[]
 for lo,hi in zip([0,300,500,1500,3000,6000],[300,500,1500,3000,6000,8454]):
  seg=part[lo:hi];counts=Counter(len(c[3]) for _,c in seg);short=[(x,c) for x,c in seg if len(c[3])<=3 and int(c[4])==0];den=sum(x['频率'] for x,_ in seg)
  bins.append({'区间':f'{lo+1}–{hi}','一简':counts[1],'二简':counts[2],'三简':counts[3],'四码':counts[4],'≤三码首选':len(short),'总项数':hi-lo,'数量占比':len(short)/(hi-lo),'字频覆盖':sum(x['频率'] for x,_ in short)/den if den else None})
 shortmet=r['metrics']['characters_short'];fullmet=r['metrics']['characters_full']
 out={'id':r['id'],'共同权重分数':r['score_common'],'≤三码首选':r['efficiency']['三码及以内首选项数'],'三码覆盖':r['efficiency']['三码及以内首选字频覆盖'],'大跨':shortmet['fingering'][1],'小跨':shortmet['fingering'][2],'小指干扰':shortmet['fingering'][3],'实际全码选重率':fullmet['effective_duplication'],'字词碰撞当量':r['metrics']['character_word_collision'],'加权实际键长':sum(x['频率']*(len(c[3])+(len(c[3])<4 or int(c[4])>0)) for x,c in part)/total,'分段':bins,'分阶段接受数':r['acceptance']}
 rows.append(out)
lines=['# 第二轮：权重、步数及击拆法对照','', '7组各20000步完成。每组通过简码分配与有简让全验证、音码冻结、最终配置重新编码与增量全量一致性检查。','', '同一初始布局下比较原权重、三码奖励乘1.25、字词碰撞权重乘1.5。起点使用第一轮02与05的原始布局；不是从第一轮最终解续跑。温度沿用第一轮实际损失校准值，记录接受率。原生随机流未固定，因此单次差异包含随机波动；不能将差异全部归因于某项参数。','', '各组总分重新用同一基线权重计算后比较，不直接比较不同目标函数的原始分数。','', '|组别|共同权重分数↓|≤三码首选项数|字频覆盖|大跨|小跨|实际全码选重率|','|---|---:|---:|---:|---:|---:|---:|']
for r in rows:lines.append(f'|{r["id"]}|{r["共同权重分数"]:.3f}|{r["≤三码首选"]}/8454|{r["三码覆盖"]:.2%}|{r["大跨"]:.2%}|{r["小跨"]:.2%}|{r["实际全码选重率"]:.3%}|')
lines+=['','## 3000步与20000步基线对照','','|起点|3000步共同分数|20000步共同分数|3000步≤三码项数|20000步≤三码项数|','|---|---:|---:|---:|---:|']
for start in ['02_perturbed','05_random']:
 a=next(x for x in old['results'] if x['id']==start);b=next(x for x in rows if x['id']==start+'_baseline')
 lines.append(f'|{start}|{a["final_score"]:.3f}|{b["共同权重分数"]:.3f}|{a["final"]["三码及以内首选项数"]}|{b["≤三码首选"]}|')
lines+=['','## 分段明细','','排名单位为字音项，不是去重汉字；按已分配字音频率排序。≤三码指一二三简首选。分段互不重叠，字频覆盖以段内频率为分母，补三简不重复计数。']
for r in rows:
 lines += ['',f'### {r["id"]}','','|区间|一简|二简|三简|四码|≤三码首选项数|数量占比|段内字频覆盖|','|---|---:|---:|---:|---:|---:|---:|---:|']
 for b in r['分段']:
  f='无已分配频率' if b['字频覆盖'] is None else f'{b["字频覆盖"]:.2%}'
  lines.append(f'|{b["区间"]}|{b["一简"]}|{b["二简"]}|{b["三简"]}|{b["四码"]}|{b["≤三码首选"]}/{b["总项数"]}|{b["数量占比"]:.2%}|{f}|')
lines+=['','## 范围与限制','','击的二山与举字底凵使用02同一初始布局及基线权重，仍存在未固定随机流的波动，不凭这一对结果定案。全部原生分项保存在各组result.json，包括分层手感、当量、热度、单字重码与字词碰撞。非核心观察项仍保持第一轮的零权重口径。本轮不修改1.0发布资料。']
(O/'第二轮对照结果.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(O/'分段与分项汇总.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{k:v for k,v in r.items() if k!='分段'} for r in rows],ensure_ascii=False))
