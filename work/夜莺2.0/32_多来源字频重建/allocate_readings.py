from pathlib import Path
import json,csv,ast,re,unicodedata,math,hashlib,html
from collections import defaultdict,Counter
P=Path(__file__).resolve().parent;W=P.parent;R=W.parents[1];S=W/'08_词库与词频重建/来源快照'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(n,v):(P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
base=read(W/'27_删利根参数0晋级赛/frozen/字音基准.json');new=read(P/'试验整字频率.json');by=defaultdict(dict)
for r in base:by[r['字']][r['拼音']]=r
# Only use established scheme readings in this experiment; supplemental candidates remain quarantined.
scope={'re':re,'unicodedata':unicodedata};tree=ast.parse((W/'03_字音频率审计/rebuild.py').read_text(encoding='utf-8-sig'));exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='syllable'],type_ignores=[]),'helpers','exec'),scope);norm=scope['syllable']
lex=defaultdict(set)
for line in (R/'repos/webchai/packages/hanzi-chai/src/data/dictionary.txt').open(encoding='utf-8-sig'):
 p=line.rstrip().split('\t')
 if len(p)>1 and len(p[0])==len(p[1].split()):lex[p[0]].add(tuple(norm(x) for x in p[1].split()))
choices={};blocked=set()
for line in (W/'08_词库与词频重建/二字词60000_鲸凉鹤补全后.jsonl').open(encoding='utf-8-sig'):
 r=json.loads(line);py=r.get('主读音') or r.get('采用拼音')
 if py:choices[r['词']]=tuple(py.split())
 else:blocked.add(r['词'])
over=read(W/'03_字音频率审计/整词读音裁决.json')
for w,r in over.items():choices[w]=tuple(r['syllables']);blocked.discard(w)
def pick(w):
 if w in blocked:return None
 p=choices.get(w)
 if p is None and len(lex[w])==1:p=next(iter(lex[w]))
 if not p or len(p)!=len(w):return None
 if any(c in by and s not in by[c] for c,s in zip(w,p)):return None
 # A bare polyphonic glyph carries no contextual evidence even if dictionary only supplies one reading.
 if len(w)==1 and len(by.get(w,{}))>1:return None
 return p
known={};totals={};unresolved={};basis={}
for tag,filename in [('新闻','bcc_news.csv'),('文学','bcc_literature.csv'),('字幕','subtlex.json'),('对话','bcc_dialogue.csv')]:
 cnt=Counter();allc=Counter();modes=Counter();un=Counter()
 if tag=='字幕':rs=read(S/filename)['data']
 else:
  with (S/filename).open(encoding='utf-8-sig',newline='') as f:rs=list(csv.DictReader(f))
 for r in rs:
  w=r['Word'] if tag=='字幕' else r['token'];n=int(float(r['WCount'] if tag=='字幕' else r['count']));p=pick(w)
  for i,c in enumerate(w):
   if c not in by:continue
   allc[c]+=n
   if p:cnt[c,p[i]]+=n;modes['整词注音匹配字次']+=n
   elif len(by[c])==1:cnt[c,next(iter(by[c]))]+=n;modes['方案单读音暂配字次']+=n
   else:un[c]+=n
 known[tag]=cnt;totals[tag]=allc;unresolved[tag]=un;basis[tag]=dict(modes)
 print(tag,'done',flush=True)
# Social source contains deduplicated character counts, not contextual reading counts.
known['社交']=Counter();totals['社交']=Counter({r['字']:r['原始来源频数']['社交'] for r in new['字表']});unresolved['社交']=totals['社交'].copy()
source_norm={s:sum(t.values()) for s,t in totals.items()};weights=new['权重'];out=[];glyph=[];method=Counter();mass=Counter()
for r in new['字表']:
 c=r['字'];opts=by[c];freq={p:0.0 for p in opts};direct={p:0.0 for p in opts};estimate={p:0.0 for p in opts};pool={p:sum(weights[s]*known[s][c,p]/source_norm[s] for s in known) for p in opts};fallbacks=[]
 for s in known:
  assert totals[s][c]==r['原始来源频数'][s],(s,c,totals[s][c],r['原始来源频数'][s])
  scale=weights[s]*1e6/source_norm[s];k={p:known[s][c,p] for p in opts};missing=totals[s][c]-sum(k.values());assert missing>=0
  if len(opts)==1:ratio={next(iter(opts)):1.0};why='方案单读音'
  elif sum(k.values())>0:ratio={p:k[p]/sum(k.values()) for p in opts};why='同来源已注音部分比例估计'
  elif sum(pool.values())>0:ratio={p:pool[p]/sum(pool.values()) for p in opts};why='跨来源加权读音比例估计'
  else:
   old={p:opts[p]['频率'] for p in opts}
   if sum(old.values())>0:ratio={p:old[p]/sum(old.values()) for p in opts};why='旧已分配比例兜底（弱证据）'
   else:ratio={p:1/len(opts) for p in opts};why='均分兜底（无比例证据）'
  if missing:
   method[why]+=1;mass[why]+=missing*scale;fallbacks.append({'来源':s,'预计次数':missing*scale,'方法':why})
  for p in opts:
   direct[p]+=k[p]*scale;estimate[p]+=missing*ratio[p]*scale;freq[p]+= (k[p]+missing*ratio[p])*scale
 assert math.isclose(sum(freq.values()),r['每百万核心字预计次数'],rel_tol=1e-10,abs_tol=1e-9)
 glyph.append({'字':c,'排名':r['新排名'],'整字频率':r['每百万核心字预计次数'],'有注音或方案单读音暂配':sum(direct.values()),'待消歧量（已用估计补齐）':sum(estimate.values()),'估计依据':fallbacks,'分音':freq})
 for p,v in freq.items():out.append({'字':c,'拼音':p,'音码':opts[p]['音码'],'频率':v,'整字频率':r['每百万核心字预计次数'],'有注音或方案单读音暂配':direct[p],'估计频率':estimate[p],'优化权重':v,'权重说明':'自然估计频率'})
# Independent optimization overlay; never alter natural totals.
for a in out:
 if a['字']=='谁':a['优化权重']=0 if a['拼音']=='shei' else a['整字频率']/4;a['权重说明']='既有谁字优化规则；不是自然频率'
assert len(out)==len(base) and math.isclose(sum(a['频率'] for a in out),1e6,abs_tol=1e-6)
out.sort(key=lambda a:(-a['频率'],a['字'],a['拼音']))
write('分音字频_试验.json',out);write('逐字分音守恒.json',glyph)
summary={'状态':'估计试验版，未替换正式输入','字数':len(glyph),'字音项':len(out),'自然频率合计':sum(a['频率'] for a in out),'待消歧但估计补齐次数':sum(a['估计频率'] for a in out),'估计方法次数':dict(method),'估计方法频率':dict(mass),'来源分配依据':basis,'限制':['词频表缺上下文；单字多音和词的多读情形不能得到真实比例。','词语主读音只是候选注音，整词匹配不等于逐次语境标注。','未分配量在证据层保留，在实验层用来源比例/旧比例/均分估计补齐，绝不当零频丢弃。','候选补充读音7项未混入；本实验沿用8454项以控制变量。','方案单读音暂配不是证明该字只有一个读音。']}
write('分音分配核验.json',summary)
(P/'分音字频_试验.txt').write_text('字\t拼音\t小鹤双拼\t每百万字分音估计频率\t其中估计补齐\t独立优化权重\n'+''.join(f"{a['字']}\t{a['拼音']}\t{a['音码']}\t{a['频率']:.8f}\t{a['估计频率']:.8f}\t{a['优化权重']:.8f}\n" for a in out),encoding='utf-8')
page='<!doctype html><meta charset="utf-8"><title>分音字频试验</title><style>body{font:16px/1.65 system-ui;margin:25px;background:#f4f7fb}table{border-collapse:collapse;background:white}td,th{padding:8px;border:1px solid #ccd}th{position:sticky;top:0;background:#dce9f3}</style><h1>分音字频 · 估计试验版</h1><p>保留整字总频，按来源分配。词频表缺语境，比例有估计，不能视为真实读音频率。谁的优化规则独立保存。未运行正式晋级赛。</p><pre>'+html.escape(json.dumps(summary,ensure_ascii=False,indent=2))+'</pre><input id="q" placeholder="查字或拼音"><table><thead><tr><th>字</th><th>拼音</th><th>双拼</th><th>分音估计频率</th><th>其中估计补齐</th><th>独立优化权重</th></tr></thead><tbody>'
for a in out:page+='<tr>'+''.join('<td>'+html.escape(str(round(v,6) if isinstance(v,float) else v))+'</td>' for v in [a['字'],a['拼音'],a['音码'],a['频率'],a['估计频率'],a['优化权重']])+'</tr>'
page+='</tbody></table><script>q.oninput=()=>document.querySelectorAll("tbody tr").forEach(r=>r.hidden=!r.textContent.includes(q.value.trim()))</script>'
(P/'分音字频试验.html').write_text(page,encoding='utf-8');print(json.dumps(summary,ensure_ascii=False))
