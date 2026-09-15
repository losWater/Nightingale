from pathlib import Path
from collections import defaultdict,Counter
import json,runpy,hashlib
O=Path(__file__).resolve().parent;A=O.parent/'08_词库与词频重建'
m=runpy.run_path(str(A/'auto_review.py'))
read=lambda p:[json.loads(l) for l in p.open(encoding='utf-8')]
latest=read(A/'二字词60000_鲸凉鹤补全后.jsonl');known={r['词'] for r in latest}
accepted={'沿用通过','自动确定主读','单音字组合通过','高频逐项核对候选','鲸凉鹤唯一读音补全候选'}
pool=[dict(r,实验码=r['主读双拼']) for r in latest if r['处理分类'] in accepted]
for r in read(A/'读音通过_候选.jsonl'):
 if r['词长']!=2 or r['词'] in known:continue
 status,py,reason,alts=m['decide'](r)
 if status not in accepted:continue
 pool.append(dict(r,实验码=''.join(m['dc'](x) for x in py.split()),处理分类=status))
pool.sort(key=lambda r:r['综合排名'])
assert len({r['词'] for r in pool})==len(pool)
assert all(len(r['实验码'])==4 for r in pool)
N=min(60000,len(pool));K=min(40000,N)
base=pool[:N];mixed=pool[:K];seen={r['实验码'] for r in mixed};chosen={r['词'] for r in mixed};novel=[]
for r in pool[K:]:
 if len(mixed)>=N:break
 if r['实验码'] not in seen:
  mixed.append(r);novel.append(r);seen.add(r['实验码']);chosen.add(r['词'])
fallback=0
for r in pool[K:]:
 if len(mixed)>=N:break
 if r['词'] not in chosen:mixed.append(r);chosen.add(r['词']);fallback+=1
assert len(mixed)==N and len(chosen)==N
assert {r['词'] for r in pool[:K]} <= chosen
assert len({r['实验码'] for r in novel})==len(novel)
groups=defaultdict(list)
for r in pool:groups[r['实验码']].append(r)
def measure(rows):
 codes={r['实验码'] for r in rows}
 mass=sum(r['排序指数'] for r in pool)
 return {'词数':len(rows),'独立码位':len(codes),'重复占位词数':len(rows)-len(codes),'全候选码位覆盖率':len(codes)/len(groups),'全候选排序指数覆盖率':sum(r['排序指数'] for r in pool if r['实验码'] in codes)/mass}
summary={'候选池词数':len(pool),'候选池码位':len(groups),'基底常用词数':K,'直接高频':measure(base),'常用加补位':measure(mixed),'补入新码位词数':len(novel),'不足名额按频次回填':fallback}
for name,rows in [('直接高频词集.jsonl',base),('常用加补位词集.jsonl',mixed),('新增码位代表词.jsonl',novel)]:
 (O/name).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
basecodes={r["实验码"] for r in base};mixedcodes={r["实验码"] for r in mixed}
weights=[]
for code,rs in sorted(groups.items()):
 counts=defaultdict(float)
 for r in rs:
  for source,value in r['各源原始词频'].items():
   if value is not None:counts[source]+=value
 weights.append({'码位':code,'代表词':rs[0]['词'],'同码词数':len(rs),'排序指数合计':sum(r['排序指数'] for r in rs),'各源词频合计':dict(counts),'说明':'原始词频各源独立汇总，不跨源相加；排序指数不是实测频率','直接高频覆盖':code in basecodes,'补位覆盖':code in mixedcodes})
(O/'全候选码位权重.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in weights),encoding='utf-8')
summary['输入指纹']={n:hashlib.sha256((A/n).read_bytes()).hexdigest() for n in ['二字词60000_鲸凉鹤补全后.jsonl','读音通过_候选.jsonl','auto_review.py']}
(O/'实验摘要.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
a=summary['直接高频'];b=summary['常用加补位']
lines=['# 字词避重选词实验','',f'可用候选池{len(pool):,}词、{len(groups):,}个四码码位。优先使用最新复核结果；原前60000词待核项不从旧表重新引入，外围候选沿用同一分歧检查。','',f'比较等量{N:,}词：直接按综合排名选取，与保留前{K:,}个可用常用词再补不同码位。这里的常用前40000指排除待核后的可用候选，不是原词频表前40000。','', '|指标|直接高频|常用加补位|','|---|---:|---:|']
for k in ['词数','独立码位','重复占位词数']:lines.append(f'|{k}|{a[k]:,}|{b[k]:,}|')
for k in ['全候选码位覆盖率','全候选排序指数覆盖率']:lines.append(f'|{k}|{a[k]:.2%}|{b[k]:.2%}|')
lines += ['',f'补入{len(novel):,}个此前未覆盖码位；新码位不足时按原排序回填{fallback:,}词。独立码位净增加{b["独立码位"]-a["独立码位"]:,}个。','', '## 口径与限制','', '- 只测选词覆盖，不代表已经减少多少实际字词重码；尚未运行2.0退火。','- 码位排序指数汇总使用整个共同候选池，避免选一个代表词后丢掉同码词贡献。原始词频分来源保存，未跨来源直接相加。','- 排序指数覆盖率不是实测文本覆盖率。候选读音和词条质量仍有未逐词验证部分。','- 当前根键位未定，本实验不使用1.0键位声称2.0避重成绩。','', '## 前20个补入的新码位','', '|词|码|原综合排名|','|---|---|---:|']
lines += [f'|{r["词"]}|{r["实验码"]}|{r["综合排名"]}|' for r in novel[:20]]
(O/'选词对照结果.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='输入指纹'},ensure_ascii=False))
