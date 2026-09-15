from pathlib import Path
import json,html,hashlib,re
P=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf8'))
a=read(P/'测评明细.json');native=read(P/'原生结果.json')
native['原系数']=read(P.parent/'43_保护范围审计与跨排多种子复核/s2_w50/result.json')
native.update({k:read(P.parent/'46_主读音硬约束字词避重'/k/'result.json') for k in ['硬约束2倍','硬约束4倍']})
f=lambda x:f'{x:.6f}'
def table(h,rows):return '<div class="scroll"><table><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in h)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in rows)+'</table></div>'
s='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>字词避重中间权重</title><style>body{font:16px/1.7 system-ui;background:#f4f7fb;color:#234;margin:28px}table{border-collapse:collapse;background:white}td,th{border:1px solid #ccd;padding:8px}.scroll{overflow:auto}</style><h1>字词避重中间权重试跑</h1><p>新增2.5倍（0.25）、3倍（0.30），复用46号2倍、4倍及原布局对照。共同起点为43号s2_w50，种子202609121702，均各5万步；字频、当量60/60/40/25/15、跨排保护50%、1643字主读音硬约束不变。每次不满足主音至少一处首选的提案无条件拒绝。</p><p>这是同一种子的权重对照，不能据此宣称多种子稳定性。其他读音另外列出。</p>'

manifest=read(P/'主读音保护清单.json')['字表'];gates=[]
for label,res in native.items():
 lines=[l.split('\t') for l in (Path(res['输出目录'])/'code.txt').read_text().splitlines()];fail=[]
 for m in manifest:
  r=lines[m['输入索引']];assert r[0]==m['字']
  if not ((r[1] and int(r[2])==0) or (r[3] and int(r[4])==0)):fail.append({'字':m['字'],'拼音':m['拼音'],'全码':r[1],'全码位次':int(r[2])+1,'简码':r[3],'简码位次':int(r[4])+1})
 other_fail=[]
 for m in read(P/'其他读音清单.json'):
  r=lines[m['输入索引']];assert r[0]==m['字']
  if not ((r[1] and int(r[2])==0) or (r[3] and int(r[4])==0)):other_fail.append({'字':m['字'],'拼音':m['拼音'],'全码':r[1],'简码':r[3]})
 gates.append({'方案':label,'通过':not fail,'未达标':fail,'其他读音未达标':other_fail})
(P/'主读音准入结果.json').write_text(json.dumps(gates,ensure_ascii=False,indent=2),encoding='utf8')
s+='<section><h2>本轮结论</h2><p><strong>2.5倍在降低字词软碰撞的同时改善累计当量，是值得复核的候选；3倍最终原生码表与起点完全相同。全部通过1643字主读音保护。</strong></p><table><tr><th>指标</th><th>原方案</th><th>2.5倍</th><th>得失</th></tr><tr><td>字词软碰撞指标</td><td>36.802411</td><td>24.132219</td><td>下降34.43%</td></tr><tr><td>前500键均当量</td><td>1.313208</td><td>1.309457</td><td>改善</td></tr><tr><td>前1500键均当量</td><td>1.315839</td><td>1.314280</td><td>改善</td></tr><tr><td>301–500键均当量</td><td>1.324350</td><td>1.321624</td><td>改善</td></tr><tr><td>501–1500键均当量</td><td>1.326477</td><td>1.333785</td><td>变差</td></tr><tr><td>前1500三码内字数</td><td>1365</td><td>1360</td><td>减少5字</td></tr><tr><td>1501–3000非首选字数</td><td>4</td><td>13</td><td>增加9字</td></tr><tr><td>3001–6000非首选字数</td><td>83</td><td>118</td><td>增加35字</td></tr><tr><td>原生同指大跨排</td><td>0.008168</td><td>0.009035</td><td>变差</td></tr><tr><td>原生同指小跨排</td><td>0.085876</td><td>0.085589</td><td>改善</td></tr><tr><td>原生小指干扰</td><td>0.033487</td><td>0.043094</td><td>变差</td></tr></table><p>前1500三码内覆盖91.00%→90.67%。后两档缺字分别为2、38字，与对照相同；表中非首选为盒子整字口径。字词软碰撞是加权指标，不是冲突对数。原生指法按训练字音权重计算，与盒子累计当量口径不同。</p><p>所有分段得失、选重与键盘负载见下表。保留原参数及2.5倍备选，建议下一步配对多种子复核；本轮只新增两次5万步，不宣称2.5倍已经稳定最优。</p></section>'
s+='<h2>1643字主读音准入结果</h2>'+table(['组','通过','不达标字'],[[g['方案'],g['通过'],'、'.join(x['字'] for x in g['未达标'])] for g in gates])
for g in gates:
 if g['未达标']:s+='<p>'+g['方案']+'不推荐为最终候选：'+html.escape(str(g['未达标']))+'</p>'
s+='<h2>其他读音未达标（不影响主音准入）</h2>'+table(['组','读音与码'],[[g['方案'],g['其他读音未达标']] for g in gates])
s+='<h2>分段当量</h2>'

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
s+='<details><summary>全部原生指标及相对原系数的变化</summary><p>指法数组的各项按引擎定义；字段保留计算，各组只调整字词软碰撞惩罚系数。覆盖率等指标增加为改善，不能把所有负差都当改善。</p>'
s+=table(['字段']+[x['方案'] for x in a],[[k]+[f(maps[x['方案']][k])+' ('+f(maps[x['方案']][k]-maps['原系数'][k])+')' if k in maps[x['方案']] else '—' for x in a] for k in maps['原系数']])+'</details>'

s+='<h2>搜索内硬约束</h2>'
rejects=[]
for job in read(P/'jobs.json'):
 label=job['id']
 log=(P/label/'五万步/stderr.log').read_text(encoding='utf8')
 count=int(re.search(r'PRIMARY_INFEASIBLE_REJECTED (\d+)',log)[1])
 rejects.append({'方案':label,'拒绝不可行提案':count,'占提案比例':count/50000})
s+=table(['组','不合格提案拒绝数','占50000步比例'],[[r['方案'],r['拒绝不可行提案'],f(r['占提案比例'])] for r in rejects])
(P/'硬约束拒绝统计.json').write_text(json.dumps(rejects,ensure_ascii=False,indent=2),encoding='utf8')

s+='<h2>普通单字表</h2>'
for x in a:
 path=Path(read(P/'码表路径.json')[x['方案']])
 s+=f'<p><a href="{path.as_uri()}">{x["方案"]}普通单字表</a></p>'
s+='</html>';(P/'字词避重对照.html').write_text(s,encoding='utf8')
summary={'分段':[{x['方案']:[b['键均'] for b in x['分档']]} for x in a],'累计':cumulative,'原生':metrics,'前1500选重':risks}
(P/'结果摘要.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
resources=[json.loads(l) for l in (P/'resources.jsonl').read_text().splitlines()]
audit={'重新编码复核通过':all(v['复核'] for v in native.values()),'最大缓存差':max(abs(v['缓存差异']) for v in native.values()),'最低可用内存GiB':min(r['availableGiB'] for r in resources),'最低E盘可用GiB':min(r['EfreeGiB'] for r in resources)}
(P/'最终核验.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(summary,ensure_ascii=False),flush=True)