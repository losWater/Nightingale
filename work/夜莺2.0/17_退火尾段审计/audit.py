from pathlib import Path
import re,json,statistics,yaml,html
P=Path(__file__).resolve().parent;T=P.parent/'15_自动晋级赛'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
finals=read(T/'最终五名.json');ids={r['id'] for r in finals}
pat=re.compile(r'已执行 (\d+) 步，当前温度 ([^，]+)，当前分数 ([^，]+)|系统搜索到了一个更好的方案，分数为 ([^，]+)|方案文件保存于 [^\n]*?solution-(\d+)\.yaml')
results=[]
for card in read(T/'cards.json'):
 d=T/'jobs'/card['id'];s=(d/'search/stdout.log').read_text(encoding='utf-8');best=float('inf');samples={};events=[];saved={};pending=None;step=0
 for m in pat.finditer(s):
  if m[1] is not None:
   step=int(m[1]);current=float(m[3]);best=min(best,current);samples[step]={'current':current,'best':best,'temperature':float(m[2])}
  elif m[4] is not None:
   score=float(m[4]);old=best;best=min(best,score)
   if pending is not None:saved[pending]=score;pending=None
   if score<old:events.append({'lower_step':step,'score':score,'improvement':old-score})
  else:pending=int(m[5])
 assert set(samples)==set(range(0,20001,2000)) and 0 in saved
 log=(d/'search/stderr.log').read_text(encoding='utf-8');a=re.search(r'TRIAL_ACCEPT \[(.*?)\] / \[(.*?)\]',log)
 accepted=[int(x) for x in a[1].split(',')];attempted=[int(x) for x in a[2].split(',')]
 r={'id':card['id'],'samples':samples,'saved_scores':saved,'improvement_last2000':samples[18000]['best']-samples[20000]['best'],'improvement_last4000':samples[16000]['best']-samples[20000]['best'],'improvement_last200':saved[0]-min(saved.values()),'strict_visible_updates_last2000':sum(e['lower_step']==18000 for e in events),'saved_updates_last200':len(saved)-1,'last_third_accepted':accepted[2],'last_third_attempted':attempted[2],'last_third_acceptance':accepted[2]/attempted[2]}
 if card['id'] in ids:
  out=Path(read(d/'optimized.json')['code']).parent
  # 只解析小型mapping块，避免载入每个快照内5MB的重复配置。
  def mapping(file):
   block=file.read_text(encoding='utf-8').split('  mapping:\n',1)[1].split('\n  ',1)[0] if False else None
   lines=file.read_text(encoding='utf-8').splitlines();start=lines.index('  mapping:')+1;result={}
   for line in lines[start:]:
    if line and not line.startswith('    '):break
    m=re.fullmatch(r'    (G\d+): ([a-z])',line)
    if m:result[m[1]]=m[2]
   assert len(result)==134;return result
  ms=[mapping(out/f'solution-{i}.yaml') for i in sorted(saved)];initial=ms[0];final=ms[-1]
  r['last200_changed_groups']=[k for k in initial if initial[k]!=final[k]]
  r['last200_adjacent_solution_changes']=[sum(a[k]!=b[k] for k in a) for a,b in zip(ms,ms[1:])]
  r['last200_moves']={k:[initial[k],final[k]] for k in r['last200_changed_groups']}
 results.append(r)
summary={'runs':len(results),'improved_last2000':sum(r['improvement_last2000']>0 for r in results),'improved_last200':sum(r['improvement_last200']>0 for r in results),'with_saved_updates_last200':sum(r['saved_updates_last200']>0 for r in results),'median_last2000':statistics.median(r['improvement_last2000'] for r in results),'median_last200':statistics.median(r['improvement_last200'] for r in results),'median_acceptance_last_third':statistics.median(r['last_third_acceptance'] for r in results)}
(P/'尾段审计.json').write_text(json.dumps({'summary':summary,'runs':results},ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 两万步尾段审计','','只读取原记录，没有重新退火。进度每2000步打印的是当前解，不是历史最优；此处结合更优解事件恢复日志精度下的最优分数。退火原生分越低越好，与百分制综合分不同。','', '保存参数report_after=0.99，solution-0是19800步时强制保存的历史最优，后续solution是剩余约200步的新最优。日志不含每次更新的精确步号，只能定位到区间；打印数值舍入可能隐藏小幅更新。','', '接受次数统计覆盖最后约6666步，不能当成最后200步，也不等于有效改进次数；其中可能有等分或轻微变差的接受。早期checkpoint只保留最后一个，因此无法从文件重建18000步的根布局。','', '总体统计：'+json.dumps(summary,ensure_ascii=False),'','|方案|18000步最优|20000步最优|末2000步改善|末200步改善|末200步新最优次数|末200步净换位根组数|','|---|---:|---:|---:|---:|---:|---:|']
for f in finals:
 r=next(x for x in results if x['id']==f['id'])
 lines.append(f"|{r['id']}|{r['samples'][18000]['best']:.3f}|{r['samples'][20000]['best']:.3f}|{r['improvement_last2000']:.3f}|{r['improvement_last200']:.3f}|{r['saved_updates_last200']}|{len(r['last200_changed_groups'])}|")
 lines+=[]
lines+=['','## 五个候选的最优分数轨迹','','|步数|'+'|'.join(r['id'] for r in finals)+'|','|---|'+'---:|'*5]
for step in range(0,20001,2000):lines.append('|'+str(step)+'|'+ '|'.join(f"{next(x for x in results if x['id']==f['id'])['samples'][step]['best']:.3f}" for f in finals)+'|')
rootnames={f'G{g["序号"]:03d}':g['根组'] for g in read(T/'frozen/当前完整根表.json')['根组']}
for f in finals:
 r=next(x for x in results if x['id']==f['id']);lines+=['', '## '+f['id']+'：最后约200步净变化','']
 lines+=['、'.join(rootnames[k]+': '+v[0]+'→'+v[1] for k,v in r['last200_moves'].items()) or '无净换位']
 lines+=['','相邻保存最优方案的变化根组数：'+str(r['last200_adjacent_solution_changes'])]
(P/'两万步尾段审计.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
for f in finals:
 r=next(x for x in results if x['id']==f['id']);print(json.dumps({k:v for k,v in r.items() if k not in ['samples','saved_scores']},ensure_ascii=False))
