from pathlib import Path
from collections import Counter,defaultdict
import csv,json,math,hashlib,html
P=Path(__file__).resolve().parent;W=P.parent;S=W/'08_词库与词频重建/来源快照'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def csvrows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:yield from csv.DictReader(f)
base=read(W/'27_删利根参数0晋级赛/frozen/字音基准.json');core={r['字'] for r in base};current=Counter()
for r in base:current[r['字']]+=r['频率']
assert len(core)==8105
counts={};audits={};paths=[]
for name,file in [('新闻','bcc_news.csv'),('文学','bcc_literature.csv'),('对话','bcc_dialogue.csv'),('字幕','subtlex.json')]:
 f=S/file;paths.append(f);cnt=Counter();seen=set();nr=0;invalid=0
 rs=read(f)['data'] if name=='字幕' else csvrows(f)
 for r in rs:
  token=r['Word'] if name=='字幕' else r['token'];v=float(r['WCount'] if name=='字幕' else r['count']);assert token not in seen;seen.add(token);nr+=1
  if not math.isfinite(v) or v<0:invalid+=1;continue
  assert v.is_integer()
  for ch in token:
   if ch in core:cnt[ch]+=int(v)
 counts[name]=cnt;audits[name]={'文件':str(f),'词条数':nr,'核心覆盖字数':len(cnt),'核心字次':sum(cnt.values()),'异常频数条目':invalid,'算法':'词条出现频次按字符逐个累加，包含单字词、重复字多次计数；未过滤歧义读音。','限制':'输入词频表的截断、分词和原始语料重复程度未完全验证；是现有来源快照内的统计。'}
f=S/'cld.csv';paths.append(f);cs=defaultdict(set)
for r in csvrows(f):
 for i in range(1,5):
  ch=r['C'+str(i)];v=r['C'+str(i)+'FrequencyRawWeibo']
  if ch not in core or v in ['NA','']:continue
  n=float(v);assert math.isfinite(n) and n>=0 and n.is_integer();cs[ch].add(int(n))
assert all(len(v)==1 for v in cs.values());counts['社交']=Counter({ch:next(iter(v)) for ch,v in cs.items()})
audits['社交']={'文件':str(f),'核心覆盖字数':len(cs),'核心字次':sum(counts['社交'].values()),'算法':'CLD的C1–C4FrequencyRawWeibo按字去重；同字频数一致性核验通过。不把同一字频在不同词中重复累加。','限制':'仅覆盖CLD词表包含的字，未覆盖不表示真实零频；不是微博全量语料。'}
profiles={'建议版':{'新闻':.2,'文学':.2,'字幕':.3,'对话':.2,'社交':.1},'五源等权':{'新闻':.2,'文学':.2,'字幕':.2,'对话':.2,'社交':.2},'偏书面':{'新闻':.3,'文学':.3,'字幕':.2,'对话':.1,'社交':.1},'偏口语':{'新闻':.1,'文学':.1,'字幕':.4,'对话':.3,'社交':.1}}
probs={s:{c:counts[s][c]/sum(counts[s].values()) for c in core} for s in counts};scores={};order={}
for label,weights in profiles.items():
 assert abs(sum(weights.values())-1)<1e-12
 scores[label]={c:sum(weights[s]*probs[s][c] for s in weights) for c in core};assert abs(sum(scores[label].values())-1)<1e-10
 order[label]=sorted(core,key=lambda c:(-scores[label][c],c))
order['当前已分配']=sorted(core,key=lambda c:(-current[c],c))
order['形码盒子']=[l.split('\t')[0] for l in (W/'30_形码盒子1.0复测/默认字频.txt').read_text().strip().splitlines()]
ranks={k:{c:i for i,c in enumerate(v,1)} for k,v in order.items()};comparisons=[]
for target in ['当前已分配','形码盒子','五源等权','偏书面','偏口语']:
 for n in [500,1500,3500]:
  a=set(order['建议版'][:n]);b=set(order[target][:n]);comparisons.append({'对照':target,'范围':n,'重合字':len(a&b),'重合率':len(a&b)/n,'各方不同':n-len(a&b),'建议版独有':[c for c in order['建议版'][:n] if c not in b],'对照独有':[c for c in order[target][:n] if c not in a]})
rank_by_count={}
for i,ch in enumerate(order['当前已分配'],1):rank_by_count.setdefault(current[ch],i)
ranks['当前已分配']={ch:rank_by_count[current[ch]] for ch in core}
rows=[]
for c in order['建议版']:
 row={'字':c,'新排名':ranks['建议版'][c],'当前排名':ranks['当前已分配'][c] if current[c]>0 else None,'盒子排名':ranks['形码盒子'].get(c),'每百万核心字预计次数':scores['建议版'][c]*1e6,'来源覆盖数':sum(counts[s][c]>0 for s in counts),'排名提升':ranks['当前已分配'][c]-ranks['建议版'][c] if current[c]>0 else None,'来源贡献':{s:profiles['建议版'][s]*probs[s][c]*1e6 for s in counts},'原始来源频数':{s:counts[s][c] for s in counts}}
 rows.append(row)
write(P/'试验整字频率.json',{'状态':'多来源试验版，未接入退火，尚未生成分读音表','权重':profiles['建议版'],'归一化':'每来源在相同8105核心字内归一化，然后加权；不是原始语料的真实整体占比。未覆盖字为本次来源内零计数，不断言真实零频。','字表':rows})
write(P/'来源核验.json',{'来源':audits,'sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in paths},'未混入':['BCC综合表（避免与分领域重复）','旧评测一万句','简单鹤鲸凉鹤词频','读音特殊优化权重'],'正频覆盖':sum(scores['建议版'][c]>0 for c in core)})
write(P/'权重敏感性与交集.json',{'权重':profiles,'交集':comparisons,'各版本字序':order})
# Portable ordinary text is probability per million, explicitly not observed frequency.
(P/'试验整字频率.txt').write_text('字\t新排名\t每百万核心字预计次数\n'+''.join(f"{r['字']}\t{r['新排名']}\t{r['每百万核心字预计次数']:.8f}\n" for r in rows),encoding='utf-8')
def table(headers,data):return '<table><thead><tr>'+''.join('<th>'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(str(v) if v is not None else '无已分配／表外')+'</td>' for v in rr)+'</tr>' for rr in data)+'</tbody></table>'
page='<!doctype html><meta charset="utf-8"><title>多来源字频试验</title><style>body{font:16px/1.65 system-ui;background:#f4f7fb;color:#234;margin:30px}table{border-collapse:collapse;background:white}th,td{padding:8px;border:1px solid #ccd}th{position:sticky;top:0;background:#dce9f3}input{padding:10px;font:inherit}p{max-width:1200px}</style><h1>多来源整字频率 · 第一版试验</h1><p>新闻20%、文学20%、字幕30%、对话20%、社交10%。每个来源先按相同8105字归一化，再加权。全部频次参与，不因读音未消歧扣除。交集严格取N字（同频按Unicode）；当前排名显示同频同名次。不修改当前退火。</p><p>社交使用CLD自带微博单字频数去重；其字表覆盖有限。新闻、文学、对话和字幕从现有词频表逐字累加，尚不能保证来源全量性、分词可比性或跨来源不重叠。因此是试验频率，不是已验证的通用标准。尚未生成分读音权重。</p>'
page+='<h2>交集与权重敏感性</h2>'+table(['与建议版比较','前N字','重合字','重合率','各方不同'],[[r['对照'],r['范围'],r['重合字'],f"{r['重合率']:.2%}",r['各方不同']] for r in comparisons])
page+='<h2>值得关注的字</h2>';lookup={r['字']:r for r in rows};focus=[lookup[c] for c in '谁的我你是了嗨嘿呃噢袁蒋秦赵法国政经亲台争']
page+=table(['字','新排名','当前排名','盒子排名','每百万字'],[[r['字'],r['新排名'],r['当前排名'],r['盒子排名'],round(r['每百万核心字预计次数'],2)] for r in focus])
changes=sorted([r for r in rows if r['排名提升'] is not None and min(r['新排名'],r['当前排名'])<=1500],key=lambda r:-abs(r['排名提升']))
page+='<h2>至少一版前1500，变化最大前50字</h2>'+table(['字','新排名','当前排名','提升名次','盒子排名'],[[r['字'],r['新排名'],r['当前排名'],r['排名提升'],r['盒子排名']] for r in changes[:50]])
page+='<h2>完整新表（按新排名）</h2><input id="q" placeholder="查字"><div id="all">'+table(['字','新排名','当前排名','盒子排名','每百万字','新闻贡献','文学贡献','字幕贡献','对话贡献','社交贡献'],[[r['字'],r['新排名'],r['当前排名'],r['盒子排名'],round(r['每百万核心字预计次数'],4),*[round(r['来源贡献'][s],4) for s in ['新闻','文学','字幕','对话','社交']]] for r in rows])+'</div><script>q.oninput=()=>document.querySelectorAll("#all tbody tr").forEach(r=>r.hidden=!r.textContent.includes(q.value.trim()))</script>'
(P/'多来源字频对照.html').write_text(page,encoding='utf-8')
print(json.dumps({'覆盖':sum(scores['建议版'][c]>0 for c in core),'交集':[{k:v for k,v in r.items() if k not in ['建议版独有','对照独有']} for r in comparisons],'重点':[{k:r[k] for k in ['字','新排名','当前排名','盒子排名']} for r in focus],'来源':audits},ensure_ascii=False))
