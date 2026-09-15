from pathlib import Path
import json,html,re,statistics
P=Path(__file__).resolve().parent
read=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
def write(name,x): (P/name).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def table(headers,rows):
 return '<div class="scroll"><table><tr>'+''.join('<th>'+html.escape(str(v))+'</th>' for v in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(f'{v:.6f}' if isinstance(v,float) else str(v))+'</td>' for v in row)+'</tr>' for row in rows)+'</table></div>'
native={k:read(v) for k,v in read(P/'结果路径.json').items()}
box={r['方案']:r for r in read(P/'测评明细.json')}
pairs=read(P/'配对.json');manifest=read(P/'主读音保护清单.json')['字表']
gates=[]
for name,res in native.items():
 lines=[l.split('\t') for l in (Path(res['输出目录'])/'code.txt').read_text(encoding='utf8').splitlines()]
 def failures(items):
  bad=[]
  for m in items:
   r=lines[m['输入索引']];assert r[0]==m['字']
   if not ((r[1] and int(r[2])==0) or (r[3] and int(r[4])==0)):
    bad.append({'字':m['字'],'拼音':m['拼音'],'全码':r[1],'全码位次':int(r[2])+1,'简码':r[3],'简码位次':int(r[4])+1})
  return bad
 bad=failures(manifest)
 gates.append({'方案':name,'通过':not bad,'未达标':bad,'其他读音未达标':failures(read(P/'其他读音清单.json'))})
assert all(g['通过'] for g in gates)
write('主读音准入结果.json',gates)
def metrics(name):
 b=box[name];m=native[name]['原生']['metric'];out={}
 for band in b['分档']:
  label=band['档位'];out[label+'键均']=band['键均'];out[label+'三码内字数']=sum(band['码长字数'][:3]);out[label+'非首选字数']=band['选重字数']
 for end in [500,1500,3000,6000]:
  items=[r for band in b['全字明细'] if band['end']<=end for r in band['items'] if 'code' in r]
  out[f'前{end}键均']=sum(r['keyEq'] for r in items)/sum(r['freq'] for r in items)
 out['前1500三码内字数']=sum(sum(r['码长字数'][:3]) for r in b['分档'][:3])
 out['字词软碰撞']=m['character_word_collision']['soft']
 for i,label in enumerate(['同手','同指大跨排','同指小跨排','小指干扰','错手','三连击']):out[label]=m['characters_short']['fingering'][i]
 return out
values={k:metrics(k) for k in native};stats=[]
for key in next(iter(values.values())):
 xs=[values[p['原权重']][key] for p in pairs];ys=[values[p['2.5倍']][key] for p in pairs]
 delta=[y-x for x,y in zip(xs,ys)];sign=1 if '三码内字数' in key else -1
 stats.append({'指标':key,'原权重均值':statistics.mean(xs),'2.5倍均值':statistics.mean(ys),'平均变化':statistics.mean(delta),'改善次数':sum(d*sign>1e-9 for d in delta),'持平次数':sum(abs(d)<=1e-9 for d in delta),'变差次数':sum(d*sign < -1e-9 for d in delta),'新增两种子改善次数':sum(d*sign>1e-9 for d in delta[1:]),'各种子变化':delta})
write('配对统计.json',{'各方案':values,'三种子统计':stats,'注意':'1702为探索样本，1703/1704为新增复核；同一起点，样本量3，不做显著性声明。'})
s='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>2.5倍字词避重多种子复核</title><style>body{font:16px/1.7 system-ui;background:#f4f7fb;color:#234;margin:28px}table{border-collapse:collapse;background:white}td,th{border:1px solid #ccd;padding:8px}.scroll{overflow:auto}summary{cursor:pointer}</style><h1>2.5倍字词避重多种子复核</h1><p>三个种子各配对原权重0.1与2.5倍0.25，每次5万步。1702复用46/47号结果；新增1703、1704。共同起点为43号s2_w50可行布局，保持字频、当量60/60/40/25/15、跨排保护50%与1643字主读音硬保护不变。</p><p>1702曾用于挑选2.5倍，需重点看新增两个种子能否重复收益。仅检验同一起点的随机稳定性，不代表不同起点泛化、显著性或全局最优。字词软碰撞是加权负担，非冲突对数；不同权重总分不可直接比较。</p>'
if (P/'结论片段.html').exists():s+=(P/'结论片段.html').read_text(encoding='utf8')
s+='<h2>三种子配对均值与一致性</h2><p>变化=2.5倍−原权重。三码内字数越多越好，其余下列成本越低越好。累计当量按各自范围字频加权后再计算种子均值。</p>'
s+=table(['指标','原权重均值','2.5倍均值','变化','改善/3','持平/3','变差/3','新增种子改善/2'],[[r[k] for k in ['指标','原权重均值','2.5倍均值','平均变化','改善次数','持平次数','变差次数','新增两种子改善次数']] for r in stats])
s+='<h2>逐种子得失</h2>'
for pair in pairs:
 a=values[pair['原权重']];b=values[pair['2.5倍']]
 s+=f'<h3>种子{pair["种子"]}</h3>'+table(['指标','原权重','2.5倍','变化'],[[k,a[k],b[k],b[k]-a[k]] for k in a])
s+='<h2>主读音保护与其他读音</h2>'+table(['组','主读音通过','未达标','其他读音未达标'],[[g['方案'],g['通过'],g['未达标'],g['其他读音未达标']] for g in gates])
s+='<h2>分档码长与选重</h2><p>盒子字频整字口径；后两档原有缺字2、38。其他读音可能影响盒子默认选码，因此与主音保护分开解释。</p>'
s+=table(['组','档位','缺字','一简','二简','三简','四码','非首选字数','加权选重率','键长','字均当量'],[[name,b['档位'],b['缺字']]+b['码长字数']+[b['选重字数'],b['选重频率'],b['键长'],b['字均']] for name,x in box.items() for b in x['分档']])
s+='<h2>键位负载（原生简码，%）</h2>'+table(['键']+list(native),[[k]+[100*r['原生']['metric']['characters_short']['key_distribution'].get(k,0) for r in native.values()] for k in 'qwertyuiopasdfghjklzxcvbnm'])
def flat(v,key=''):
 out={}
 if isinstance(v,dict):
  for k,x in v.items():out.update(flat(x,key+'/'+k))
 elif isinstance(v,list):
  for i,x in enumerate(v):out.update(flat(x,key+'/'+str(i)))
 elif isinstance(v,(int,float)):out[key]=v
 return out
maps={k:flat(v['原生']['metric']) for k,v in native.items()}
s+='<details><summary>全部原生指标</summary>'+table(['指标']+list(native),[[k]+[v.get(k,'—') for v in maps.values()] for k in next(iter(maps.values()))])+'</details>'
rejects=[]
for j in read(P/'jobs.json'):
 log=(P/j['id']/'五万步/stderr.log').read_text(encoding='utf8')
 rejects.append([j['id'],int(re.search(r'PRIMARY_INFEASIBLE_REJECTED (\d+)',log)[1])])
s+='<h2>新增任务硬约束拒绝数</h2>'+table(['组','拒绝次数/50000'],rejects)
s+='<h2>普通单字表</h2>'
for k,p in read(P/'码表路径.json').items():s+=f'<p><a href="{Path(p).as_uri()}">{html.escape(k)}</a></p>'
(P/'多种子复核.html').write_text(s+'</html>',encoding='utf8')
resources=[json.loads(l) for l in (P/'resources.jsonl').read_text(encoding='utf8').splitlines()]
audit={'全部通过保护':all(g['通过'] for g in gates),'重编码核验全部通过':all(v['复核'] for v in native.values()),'最大缓存差':max(v['缓存差异'] for v in native.values()),'最低可用内存GiB':min(r['availableGiB'] for r in resources),'最低E盘可用GiB':min(r['EfreeGiB'] for r in resources)}
write('最终核验.json',audit)
print(json.dumps({'审核':audit,'重点指标':[r for r in stats if r['指标'] in ['字词软碰撞','前500键均','前1500键均','前1500三码内字数','同指大跨排','小指干扰']]},ensure_ascii=False))
