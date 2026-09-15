from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,os,sys,random,copy,re,yaml,time
ROOT=Path(__file__).resolve().parent;F=ROOT/'frozen'
sys.path.insert(0,str(F/'vendor'))
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+f'.{os.getpid()}.tmp');tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,p)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def yload(p):return yaml.load(Path(p).read_text(encoding='utf-8'),Loader=yaml.CSafeLoader)
SET=read(ROOT/'settings.json')
def corrected(rows):
 from pypinyin import lazy_pinyin,Style
 chars=read(F/'字音基准.json');by=defaultdict(list)
 for c in chars:by[c['字']].append(c)
 words={w['词']:w['码'] for w in read(F/'固定无简词词库.json')}
 result=[];audit=Counter()
 for row in rows:
  text=row['汉字'];spans=re.findall('[一-鿿]+',row['原句']);assert ''.join(spans)==text
  tokens=[];codes=[];flags=[]
  for span in spans:
   ps=lazy_pinyin(span,style=Style.NORMAL,v_to_u=False,errors=lambda s:list(s));assert len(ps)==len(span)
   i=0
   while i<len(span):
    w=span[i:i+2]
    if w in words:
     tokens.append(w);codes.extend([words[w][:2],words[w][2:]]);flags.extend(['固定词音']*2);i+=2;continue
    c=span[i];opts=by[c];match=next((o for o in opts if o['拼音']==ps[i]),None)
    if len(opts)==1:match=opts[0];flag='单读音'
    elif match:flag='上下文工具读音'
    else:match=opts[0];flag='工具读音不匹配_主读回退'
    tokens.append(c);codes.append(match['音码']);flags.append(flag);i+=1
  assert all(any(o['音码']==code for o in by[c]) for c,code in zip(text,codes))
  row={**row,'词组切分':tokens,'音码':codes,'读音依据':flags};result.append(row);audit.update(flags)
 return result,dict(audit)
def save_corpus(rows,roundno):
 d=F/f'round{roundno}';d.mkdir(exist_ok=True)
 for n in ['当量表.tsv','字音基准.json','固定无简词词库.json']:
  import shutil;shutil.copyfile(F/n,d/n)
 rows,audit=corrected(rows);write(d/'固定一万句.json',rows)
 m={'句数':len(rows),'字次':sum(len(r['汉字']) for r in rows),'去重文本数':len({r['汉字'] for r in rows}),'读音依据':audit,'来源':dict(Counter(r['来源'] for r in rows)),'sha256':{n:sha(d/n) for n in ['当量表.tsv','字音基准.json','固定无简词词库.json','固定一万句.json']}}
 assert len(rows)==10000;write(d/'固定清单.json',m)
def prepare_first():
 if not (F/'round1/固定清单.json').exists():save_corpus(read(F/'固定一万句.json'),1)
def prepare_second():
 if (F/'round2/固定清单.json').exists():return
 import importlib.util
 spec=importlib.util.spec_from_file_location('extractor',F/'旧语料抽样.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 excluded={r['汉字'] for r in read(F/'round1/固定一万句.json')} | {r['汉字'] for r in read(ROOT.parent/'15_自动晋级赛/frozen/round2/固定一万句.json')};charset={r['字'] for r in read(F/'字音基准.json')};rng=random.Random(SET['second_seed']);allrows=[]
 sources=[('百科',mod.iter_wiki,'wikipedia-cn.jsonl'),('传媒',mod.iter_media_zip,'传媒领域语料库.zip'),('对话',mod.iter_lccc_zip,'LCCC-large.zip'),('网文',mod.iter_parquet,'fineweb_skypile_00000.parquet')]
 for tag,fn,name in sources:
  pool=[];seen=set();n=0
  for original,text in fn(ROOT.parent/'15_自动晋级赛/frozen/raw'/name,200000):
   if text in excluded or text in seen or not set(text)<=charset:continue
   seen.add(text);n+=1;r={'来源':tag,'原句':original,'汉字':text}
   if len(pool)<2500:pool.append(r)
   else:
    j=rng.randrange(n)
    if j<2500:pool[j]=r
  if len(pool)!=2500:raise RuntimeError(f'第二轮来源不足: {tag} {len(pool)}')
  allrows.extend(pool);excluded.update(r['汉字'] for r in pool)
 rng.shuffle(allrows);allrows=[{**r,'id':i+1} for i,r in enumerate(allrows)]
 assert len({r['汉字'] for r in allrows})==10000
 assert not {r['汉字'] for r in allrows}&{r['汉字'] for r in read(F/'round1/固定一万句.json')}
 save_corpus(allrows,2)
def bench_module(roundno,where,details=False):
 source=(F/'benchmark_base.py').read_text(encoding='utf-8')
 source=source.replace("P=Path(__file__).resolve().parent; I=P/'inputs'; A=P.parent/'12_权重与步数对照'",'P=WORK; I=INPUT; A=WORK')
 source=source.replace("write(out/(mode+'_逐句按键.json'),traces)","write(out/(mode+'_逐句按键.json'),traces) if DETAILS else None")
 source=source.replace("(out/(label+'码表.txt')).write_text", "(out/(label+'码表.txt')).write_text")
 ns={'__file__':str(F/'benchmark_base.py'),'__name__':'bench_library','WORK':Path(where),'INPUT':F/f'round{roundno}','DETAILS':details};exec(source,ns);return ns

def theory_data(native,codefile):
 es=yload(F/'elements.yaml');lines=[l.split('\t') for l in Path(codefile).read_text(encoding='utf-8').splitlines()];part=[(e,r) for e,r in zip(es,lines) if len(e['词'])==1];assert len(part)==8454
 bins=[]
 for lo,hi in zip([0,300,500,1500,3000,6000],[300,500,1500,3000,6000,8454]):
  seg=part[lo:hi];short=[(e,r) for e,r in seg if len(r[3])<=3 and int(r[4])==0];den=sum(e['频率'] for e,r in seg);cnt=Counter(len(r[3]) for e,r in seg)
  bins.append({'区间':f'{lo+1}–{hi}','数量占比':len(short)/len(seg),'字频覆盖':sum(e['频率'] for e,r in short)/den if den else None,'一简':cnt[1],'二简':cnt[2],'三简':cnt[3],'四码':cnt[4],'≤三码首选':len(short)})
 words=read(F/'固定无简词词库.json');wc=defaultdict(list)
 for i,w in enumerate(words):wc[w['码']].append(i+1)
 cb=[500,1500,3000,6000,8454];wb=[2000,5000,10000,20000,50000,60000]
 matrices={n:[[0]*6 for _ in cb] for n in ['全部单字全码','剔除有简码字音项']}
 for i,(e,r) in enumerate(part,1):
  a=next(j for j,n in enumerate(cb) if i<=n)
  for wr in wc.get(r[1],[]):
   b=next(j for j,n in enumerate(wb) if wr<=n);matrices['全部单字全码'][a][b]+=1
   if len(r[3])==4:matrices['剔除有简码字音项'][a][b]+=1
 keylen=sum(e['频率']*(len(r[3])+(len(r[3])<4 or int(r[4])>0)) for e,r in part)/sum(e['频率'] for e,r in part)
 ns={'rows':[{'id':'candidate','分段':bins,'加权实际键长':keylen}],'raw':{'candidate':{'metrics':native}},'coll':{'candidate':{'矩阵':matrices}},'cfg':read(F/'theory_rules.json')}
 source=(F/'theory_score_base.py').read_text(encoding='utf-8');exec(source[source.index('out=[]'):source.index('out.sort')],ns)
 return {'theory_old':ns['out'][0],'分段':bins,'字词矩阵':matrices}
def combine(theory,bench):
 t=bench['理论当量_统一46键表'];assert not t['缺失当量键对'] and not t['缺字音频次']
 def s(x,b,a):assert x is not None;return b/(1+x/a)
 old=theory['theory_old'];tp=next(e['得分'] for e in old['分项'] if e['项目']=='键对当量');ts=old['总分']-tp+s(t['键均当量'],1,1.3)+s(t['字均当量'],2,3)
 parts={}
 for name,d in bench['实战'].items():
  assert d['可计分']
  vals={'热力左右':s(abs(d['左手占比_不含空格']-.5),10,.05),'热力小指':s(d['小指占比_不含空格'],10,.2),'热力最高键':s(d['最高单键占比_不含空格'],10,.1),'热力最高指':s(d['最高单指占比_不含空格'],10,.25),'键均当量':s(d['键均当量'],10,1.3),'字均当量':s(d['字均当量'],20,4),'码长':s(max(0,d['每字击键']-1),20,2),'字字选重':s(d['字字选重率_单字上屏'],5,.02),'字词增量':s(d['字词增量受影响率'],5,.02)}
  parts[name]={'score':sum(vals.values()),'parts':vals}
 return {'theory':ts,'practice':parts,'total':.6*ts+.2*sum(x['score'] for x in parts.values())}
