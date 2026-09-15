from pathlib import Path
import json,html,hashlib
P=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf8'))
a=read(P/'测评明细.json');native=read(P/'原生结果.json')
native['无保护']=read(P.parent/'41_分段当量高频权重试跑/温和/result.json')
f=lambda x:f'{x:.6f}'
def table(h,rows):return '<div class="scroll"><table><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in h)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</table></div>'
s='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>温和当量跨排保护</title><style>body{font:16px/1.7 system-ui;background:#f4f7fb;color:#234;margin:28px}table{border-collapse:collapse;background:white}td,th{border:1px solid #ccd;padding:8px}th{background:#dce9f3}.scroll{overflow-x:auto}</style><h1>温和当量＋同指跨排保护</h1><p>五段当量权重固定60/60/40/25/15。无保护为41号温和组，另外两组恢复参数0中同指大跨排、小跨排原权重的25%和50%；其余手感权重仍为0，三码、重码和字词避重目标不变。每次50000步、相同初始布局及种子202609121701，原生优化后用盒子独立复测。</p><p>恢复比例是惩罚系数的比例，不是跨排率上限。单种子探索。原热力权重为0，仅观测；后两档缺2、38字，各组覆盖一致。</p><h2>分段键均当量</h2>'
s+='<p><strong>本轮50%保护组更值得保留为候选：前500键均1.309046→1.308501，前1500为1.313490→1.312136，前6000为1.315121→1.313970；原生同指大跨排1.0309%→0.7128%，小跨排8.9329%→8.3299%。</strong></p><p>代价：字词软碰撞38.296417→41.272730，盒子前1500内殊uukt为次选；25%组则有殖uisq次选。训练字音层级的保护集合与盒子整字前1500不同，所以不能仅凭原生层级选重为零就称前1500无重。本轮为单种子，应先复核稳定性与上述重码，再决定最终参数。</p>'
s+=table(['分段']+[x['方案'] for x in a],[[a[0]['分档'][i]['档位']]+[f(x['分档'][i]['键均']) for x in a] for i in range(5)])
cumulative=[]
for end in [500,1500,3000,6000]:
 row=[f'前{end}字']
 for x in a:
  items=[r for b in x['全字明细'] if b['end']<=end for r in b['items'] if 'code' in r]
  row.append(sum(r['keyEq'] for r in items)/sum(r['freq'] for r in items))
 cumulative.append(row)
s+='<h2>累计范围键均当量</h2><p>按范围内覆盖字频重新加权，不是分段均值的简单平均。</p>'+table(['范围']+[x['方案'] for x in a],[[r[0]]+[f(v) for v in r[1:]] for r in cumulative])
s+='<h2>三码、选重及实际成本</h2>'
s+=table(['组','档位','一简','二简','三简','四码','选重字数','加权选重率','实际键长','字均当量'],[[x['方案'],b['档位']]+b['码长字数']+[b['选重字数'],f(b['选重频率']),f(b['键长']),f(b['字均'])] for x in a for b in x['分档']])
s+='<h2>字词避重及原生手感</h2><p>以下为训练字音条目口径，与盒子整字档位区别。软碰撞为原目标加权负担，并非碰撞对数。不同目标的优化总分不能直接比较。</p>'
metrics=[]
for x in a:
 m=native[x['方案']]['原生']['metric'];short=m['characters_short']
 metrics.append([x['方案'],m['character_word_collision']['hard'],m['character_word_collision']['soft'],short['duplication'],short['pair_equivalence'],short.get('key_distribution_loss')])
s+=table(['组','字词硬碰撞','字词软碰撞','单字加权选重','原生键对当量','键位分布损失'],[[v if not isinstance(v,float) else f(v) for v in r] for r in metrics])
s+='<h2>原生指法逐项检查</h2><p>训练字音频率加权、按原生键对口径归一化；同手、大跨、小跨、干扰、错手、三连击按引擎定义，不能直接解释成盒子口径的同键三连或同指三连。</p>'
s+=table(['组','同手','同指大跨排','同指小跨排','小指干扰','错手','三连击'],[[x['方案']]+[f(v) for v in native[x['方案']]['原生']['metric']['characters_short']['fingering'][:6]] for x in a])
s+='<h2>键位负载（原生简码，百分比）</h2>'
keys=list('qwertyuiopasdfghjklzxcvbnm')
s+=table(['键']+[x['方案'] for x in a],[[k]+[f(100*native[x['方案']]['原生']['metric']['characters_short']['key_distribution'].get(k,0)) for x in a] for k in keys])
s+='<h2>前1500字选重明细</h2>'
risks=[]
for x in a:
 for b in x['全字明细'][:3]:
  for r in b['items']:
   if r.get('collision',0)>1:risks.append([x['方案'],r['wd'],r['code'],r['collision']])
s+=table(['组','字','码','候选位置'],risks)
def flat(v,k=''):
 out={}
 if isinstance(v,dict):
  for key,x in v.items():out.update(flat(x,k+'/'+key))
 elif isinstance(v,list):
  for i,x in enumerate(v):out.update(flat(x,k+'/'+str(i)))
 elif isinstance(v,(int,float)):out[k]=v
 return out
maps={k:flat(v['原生']['metric']) for k,v in native.items()}
s+='<details><summary>全部原生指标及相对无保护的变化</summary><p>指法数组的各项按引擎定义；字段保留计算，两组仅恢复跨排惩罚系数。覆盖率等指标增加为改善，不能把所有负差都当改善。</p>'
s+=table(['字段']+[x['方案'] for x in a],[[k]+[f(maps[x['方案']][k])+' ('+f(maps[x['方案']][k]-maps['无保护'][k])+')' if k in maps[x['方案']] else '—' for x in a] for k in maps['无保护']])+'</details>'
s+='<h2>普通单字表</h2>'
for x in a:
 path=P.parent/'41_分段当量高频权重试跑/温和_五万步单字表.txt' if x['方案']=='无保护' else P/(x['方案']+'_五万步单字表.txt')
 s+=f'<p><a href="{path.as_uri()}">{x["方案"]}普通单字表</a></p>'
s+='</html>';(P/'跨排保护对照.html').write_text(s,encoding='utf8')
summary={'分段':[{x['方案']:[b['键均'] for b in x['分档']]} for x in a],'累计':cumulative,'原生':metrics,'前1500选重':risks}
(P/'结果摘要.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
resources=[json.loads(l) for l in (P/'resources.jsonl').read_text().splitlines()]
audit={'重新编码复核通过':all(v['复核'] for v in native.values()),'最大缓存差':max(abs(v['缓存差异']) for v in native.values()),'最低可用内存GiB':min(r['availableGiB'] for r in resources),'最低E盘可用GiB':min(r['EfreeGiB'] for r in resources)}
(P/'最终核验.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(summary,ensure_ascii=False),flush=True)
