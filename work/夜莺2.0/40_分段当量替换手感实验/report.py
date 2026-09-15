from pathlib import Path
import json,html,hashlib
P=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf8'))
a=read(P/'测评明细.json');native=read(P/'原生结果.json')
native['原40']=read(P.parent/'38_固定200字当量专项试跑/w40/result.json')
f=lambda x:f'{x:.6f}'
def table(h,rows):return '<div class="scroll"><table><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in h)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</table></div>'
s='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>分段当量替换手感实验</title><style>body{font:16px/1.7 system-ui;background:#f4f7fb;color:#234;margin:28px;max-width:1450px}table{border-collapse:collapse;background:white;margin:15px 0}td,th{border:1px solid #ccd;padding:8px}th{background:#dce9f3}.scroll{overflow-x:auto}.note{background:#fff1c8;padding:16px}</style><h1>分段当量替换手感实验</h1><p>同一小鹤音部、新字频、根集、起点和随机种子202609121701，每组50000步。五段：1–300、301–500、501–1500、1501–3000、3001–6000。每段先按盒子字频独立归一化，再以同等系数40加入目标，避免低频档被总体字频淹没。</p><p>原40：只加301–500专项目标的历史对照。叠加：保留原手感惩罚，再加五段当量。替换：原手感连击、跨排、音形衔接、整体当量惩罚清零，以五段当量替代；三码覆盖、重码及字词碰撞参数不变。</p><p class="note">单种子探索，不能证明普遍优势。原配置键盘负载权重为0，本轮保持原值，热力与指法作为独立验收指标；低当量不代表它们一定更好。目标仍使用原生候选位置近似；下方当量来自盒子独立复测。后两档缺2、38字，各组缺字一致。</p><h2>五段键均当量</h2>'''
s+='<p><strong>首轮结论：替换组的后三档当量均低于原40，字词软碰撞也由48.112500降至45.785437；但前300和301–500退步，累计前6000由1.316772升至1.319820。五段等权平均则由1.332804降至1.330792。两种平均回答的问题不同，不能把等权改善当成整体输入成本改善。</strong></p><p>替换组原生同指大跨排由0.7590%升至0.8858%，小跨排由8.2940%升至8.8613%。说明低当量不足以保证每一项指法都更好。下一步可考虑提高高频档权重，同时保留少量关键指法限制；本轮不据单种子结果定稿。</p>'
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
s+='<details><summary>全部原生指标及相对原40的变化</summary><p>指法数组的各项按引擎定义；字段保留计算，替换组只是清零其损失权重。覆盖率等指标增加为改善，不能把所有负差都当改善。</p>'
s+=table(['字段']+[x['方案'] for x in a],[[k]+[f(maps[x['方案']][k])+' ('+f(maps[x['方案']][k]-maps['原40'][k])+')' if k in maps[x['方案']] else '—' for x in a] for k in maps['原40']])+'</details>'
s+='<h2>普通单字表</h2>'
for x in a:
 path=P.parent/'38_固定200字当量专项试跑/w40_五万步单字表.txt' if x['方案']=='原40' else P/(x['方案']+'_五万步单字表.txt')
 s+=f'<p><a href="{path.as_uri()}">{x["方案"]}普通单字表</a></p>'
s+='</html>';(P/'分段当量实验.html').write_text(s,encoding='utf8')
summary={'分段':[{x['方案']:[b['键均'] for b in x['分档']]} for x in a],'累计':cumulative,'原生':metrics,'前1500选重':risks}
(P/'结果摘要.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
resources=[json.loads(l) for l in (P/'resources.jsonl').read_text().splitlines()]
audit={'重新编码复核通过':all(v['复核'] for v in native.values()),'最大缓存差':max(abs(v['缓存差异']) for v in native.values()),'最低可用内存GiB':min(r['availableGiB'] for r in resources),'最低E盘可用GiB':min(r['EfreeGiB'] for r in resources)}
(P/'最终核验.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(summary,ensure_ascii=False),flush=True)
