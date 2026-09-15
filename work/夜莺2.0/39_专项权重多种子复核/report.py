from pathlib import Path
import json, html, statistics, hashlib
P=Path(__file__).resolve().parent
OLD=P.parent/'38_固定200字当量专项试跑'
read=lambda p:json.loads(p.read_text(encoding='utf8'))
a=read(P/'测评明细.json');by={x['方案']:x for x in a};native=read(P/'原生结果.json')
for w in [0,40,120]:native[f's1_w{w}']=read(OLD/f'w{w}'/'result.json')
seeds=[1,2,3];weights=[0,40,120];mean=statistics.mean
f=lambda x:f'{x:.6f}'
def tab(h,rows):
 return '<div class="scroll"><table><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in h)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in r)+'</tr>' for r in rows)+'</table></div>'
def values(w,fn):return [fn(by[f's{s}_w{w}'],native[f's{s}_w{w}']['原生']['metric']) for s in seeds]
summary=[]
for w in weights:
 vals=values(w,lambda x,m:x['分档'][1]['键均'])
 diff=[by[f's{s}_w{w}']['分档'][1]['键均']-by[f's{s}_w0']['分档'][1]['键均'] for s in seeds]
 summary.append({'权重':w,'目标键均平均':mean(vals),'最小':min(vals),'最大':max(vals),'配对差平均':mean(diff),'逐种子配对差':diff,'改善次数':sum(d<-1e-9 for d in diff),'字词软碰撞平均':mean(values(w,lambda x,m:m['character_word_collision']['soft'])),'目标四码字平均':mean(values(w,lambda x,m:x['码长字数'][3])),'目标实际键长平均':mean(values(w,lambda x,m:x['分档'][1]['键长']))})
(P/'汇总.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
s='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>专项权重多种子复核</title><style>body{font:16px/1.7 system-ui;background:#f4f7fb;color:#234;margin:28px;max-width:1450px}table{border-collapse:collapse;background:white;margin:15px 0}td,th{border:1px solid #ccd;padding:8px}th{background:#dce9f3}.scroll{overflow-x:auto}.note{background:#fff1c8;padding:15px}</style><h1>301–500档专项权重 · 多种子复核</h1><p>根集不变，小鹤音部、新字频、参数0、同一个初始布局，每次50000步。三个种子为202609121701、202609121702、202609121703，各自配对测试λ=0、40、120。种子1取38号冻结结果，本轮新增六次运行。</p><p class="note">目标是验证权重效果能否跨随机流复现。三个种子样本小，且起点和目标200字相同，不能称为统计显著或泛化验证。退火目标沿用38号原生候选位置近似；下表由独立盒子原生测评给出。</p><h2>目标200字：平均与波动</h2>'''
s+='<p><strong>本轮结论：40和120在三个种子上都改善目标档。40的目标均值1.327219，各档平均当量均下降；120进一步降到1.313011，但前300字平均当量上升，字词软碰撞更多，并在两个种子的盒子前1500字内出现选重。40更适合作为下一步平衡优化的基线，120保留为该档定向优化的参考。</strong></p>'
s+=tab(['额外权重','键均均值','最小—最大','配对差均值','改善种子数','字词软碰撞均值','四码字均值'],[[x['权重'],f(x['目标键均平均']),f(x['最小'])+'—'+f(x['最大']),f(x['配对差平均']),str(x['改善次数'])+'/3',f(x['字词软碰撞平均']),f(x['目标四码字平均'])] for x in summary])
s+='<h2>逐种子配对</h2>'
rows=[]
for z in seeds:
 for w in weights:
  x=by[f's{z}_w{w}'];b=by[f's{z}_w0'];m=native[f's{z}_w{w}']['原生']['metric']
  rows.append([z,w,f(x['分档'][1]['键均']),f(x['分档'][1]['键均']-b['分档'][1]['键均']),sum(x['码长字数'][:3]),f(x['分档'][1]['键长']),f(x['分档'][1]['字均']),m['character_word_collision']['hard'],f(m['character_word_collision']['soft'])])
s+=tab(['种子','权重','目标键均','相对本种子基线','目标≤三码字数','实际加权键长','目标字均当量','字词硬碰撞','字词软碰撞'],rows)
s+='<h2>全部档位：三种子均值</h2><p>括号为同种子配对差的均值，负值表示当量下降。后两档分别缺2、38字，各组覆盖字集相同，按覆盖频率归一化。</p>'
s+=tab(['档位']+[f'权重{w}' for w in weights],[[a[0]['分档'][i]['档位']]+[f(mean(values(w,lambda x,m:x['分档'][i]['键均'])))+' ('+f(mean([by[f's{z}_w{w}']['分档'][i]['键均']-by[f's{z}_w0']['分档'][i]['键均'] for z in seeds]))+')' for w in weights] for i in range(5)])
cumulative=[]
for end in [500,1500,3000,6000]:
 row=[f'前{end}字']
 for w in weights:
  vals=[]
  for z in seeds:
   items=[x for band in by[f's{z}_w{w}']['全字明细'] if band['end']<=end for x in band['items'] if 'code' in x]
   vals.append(sum(x['keyEq'] for x in items)/sum(x['freq'] for x in items))
  row.append(f(mean(vals)))
 cumulative.append(row)
s+='<h2>累计范围键均当量</h2><p>每个方案先对范围内全部覆盖字按盒子字频加权，再对三个种子取平均；不是分段均值的算术平均。前3000、前6000分别缺2、40字，各组覆盖范围一致。</p>'
s+=tab(['累计范围','原权重0','专项40','专项120'],cumulative)
s+='<h2>分档三码覆盖、选重、键长</h2><p>盒子整字档位；≤三码为最短码长，非必然首选，另列选重数。与原生训练字音层级不同。</p>'
rows=[]
for i in range(5):
 for w in weights:
  bs=[by[f's{z}_w{w}']['分档'][i] for z in seeds]
  rows.append([bs[0]['档位'],w,f(mean(sum(b['码长字数'][:3]) for b in bs)),f(mean(b['选重字数'] for b in bs)),f(mean(b['选重频率'] for b in bs)),f(mean(b['键长'] for b in bs)),f(mean(b['字均'] for b in bs))])
s+=tab(['档位','权重','≤三码字数均值','选重字数均值','加权选重率','加权键长','字均当量'],rows)
s+='<h2>前1500字选重具体项</h2>'
risks=[]
for r in a:
 for band in r['全字明细'][:3]:
  for x in band['items']:
   if x.get('collision',0)>1:risks.append([r['方案'],x['wd'],x['code'],x['collision']])
s+=tab(['方案','字','码','候选位置'],risks)
s+='<p>盒子原生collision从1计数，只有大于1才是选重。40组与对照组的三次结果，盒子前1500字均无选重。原生训练字音的保护层级与盒子整字前1500不是同一个集合。</p>'
s+='<h2>200字成本分解均值</h2><p>约64%（40组）和68%（120组）的净改善体现在第二键→第三键分项。按实际键对数归一化后加权；码长变化也会改变分母，分项不代表独立因果效应。</p>'
s+=tab(['权重','前两键','第二→第三键','第三→第四键','上屏／选重'],[[w]+[f(mean(values(w,lambda x,m:x['成本'][i]))) for i in range(4)] for w in weights])
charrows=[]
for w in [40,120]:
 for ch in [r['字'] for r in a[0]['逐字']]:
  ds=[];codes=[];freqs=[]
  for z in seeds:
   b=next(r for r in by[f's{z}_w0']['逐字'] if r['字']==ch);t=next(r for r in by[f's{z}_w{w}']['逐字'] if r['字']==ch)
   ds.append(t['当量']-b['当量']);codes.append(b['码']+'→'+t['码']);freqs.append(b['字频']/sum(r['字频'] for r in by[f's{z}_w0']['逐字']))
  charrows.append({'权重':w,'字':ch,'加权平均差':mean(d*q for d,q in zip(ds,freqs)),'平均当量差':mean(ds),'改善种子数':sum(d<-1e-9 for d in ds),'各种子码':codes})
charrows.sort(key=lambda x:(x['权重'],x['加权平均差']))
(P/'逐字配对变化.json').write_text(json.dumps(charrows,ensure_ascii=False,indent=2),encoding='utf8')
s+='<h2>改善与损失来自哪些字</h2><p>每组展示加权改善最大20字、损失最大10字，完整400条另存JSON。负数为改善。</p>'
for w in [40,120]:
 rows=[r for r in charrows if r['权重']==w]
 s+='<h3>权重'+str(w)+'</h3>'+tab(['字','平均加权差','改善种子数','种子1','种子2','种子3'],[[r['字'],f(r['加权平均差']),r['改善种子数']]+r['各种子码'] for r in rows[:20]+rows[-10:]])
def flat(v,k=''):
 out={}
 if isinstance(v,dict):
  for key,x in v.items():out.update(flat(x,k+'/'+key))
 elif isinstance(v,list):
  for i,x in enumerate(v):out.update(flat(x,k+'/'+str(i)))
 elif isinstance(v,(int,float)):out[k]=v
 return out
maps={k:flat(v['原生']['metric']) for k,v in native.items()};keys=list(maps['s1_w0'])
s+='<details><summary>全部原生指标均值与配对变化：指法、热力、重码、三码及字词避重</summary><p>字段按引擎定义，分层为训练字音条目；数值增加未必更差，覆盖数量等需反向理解。不存在的字段不算作零。</p>'
rows=[]
for k in keys:
 row=[k]
 for w in weights:
  vals=[maps[f's{z}_w{w}'].get(k) for z in seeds];base=[maps[f's{z}_w0'].get(k) for z in seeds]
  row.append('—' if None in vals+base else f(mean(vals))+' ('+f(mean(v-b for v,b in zip(vals,base)))+')')
 rows.append(row)
s+=tab(['字段']+[str(w) for w in weights],rows)+'</details><h2>码表和原始数据</h2>'
for z in seeds:
 for w in weights:
  path=OLD/f'w{w}_五万步单字表.txt' if z==1 else P/f's{z}_w{w}_五万步单字表.txt'
  s+=f'<p><a href="{path.as_uri()}">种子{z}／权重{w}普通单字表</a></p>'
s+='<p><a href="汇总.json">汇总JSON</a> · <a href="测评明细.json">盒子原始明细</a> · <a href="逐字配对变化.json">逐字配对变化</a></p></html>'
(P/'多种子复核.html').write_text(s,encoding='utf8')
h=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
jobs=read(P/'jobs.json');assert len({h(P/j['id']/'initial.json') for j in jobs})==1;assert len({h(P/j['id']/'elements.yaml') for j in jobs})==1
resources=[json.loads(l) for l in (P/'resources.jsonl').read_text().splitlines()]
audit={'新增组数':6,'包含历史总组数':9,'配置六组完全一致':True,'字音表六组完全一致':True,'最低可用内存GiB':min(r['availableGiB'] for r in resources),'最低E盘可用GiB':min(r['EfreeGiB'] for r in resources),'重新编码全部通过':all(v['复核'] for v in native.values()),'最大缓存误差':max(abs(v['缓存差异']) for v in native.values())}
(P/'最终核验.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(summary,ensure_ascii=False),flush=True)
