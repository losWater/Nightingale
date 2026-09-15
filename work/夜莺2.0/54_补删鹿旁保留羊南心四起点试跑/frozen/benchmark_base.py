from pathlib import Path
from collections import Counter,defaultdict
import json,random,hashlib,re,html,argparse
P=Path(__file__).resolve().parent; I=P/'inputs'; A=P.parent/'12_权重与步数对照'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def freeze():
 if (I/'固定清单.json').exists():return
 import yaml
 elements=yaml.safe_load((P.parent/'11_多起点试跑/elements.yaml').read_text(encoding='utf-8'))
 chars=[{'字':e['词'],'拼音':e['拼音'],'音码':''.join(x['element'][2:] for x in e['元素序列'][:2]),'频率':e['频率']} for e in elements if len(e['词'])==1]
 write(I/'字音基准.json',chars)
 words=[json.loads(l) for l in (P.parent/'09_字词避重选词实验/常用加补位词集.jsonl').read_text(encoding='utf-8').splitlines()]
 words.sort(key=lambda w:(-w['排序指数'],w['词']))
 words=[{'词':w['词'],'码':w['实验码'],'排名':i+1} for i,w in enumerate(words)]
 assert len(words)==60000 and all(len(w['词'])==2 and len(w['码'])==4 for w in words)
 write(I/'固定无简词词库.json',words)
 source=[l.split('\t') for l in (I/'旧语料快照.tsv').read_text(encoding='utf-8').split('\n')[1:] if l]
 assert len(source)==10020 and all(len(r)==4 for r in source)
 chosen=random.Random(20260912).sample(list(enumerate(source,1)),10000)
 bychar=defaultdict(list)
 for c in chars:bychar[c['字']].append(c)
 wd={w['词']:w for w in words};corpus=[]
 for n,(original,r) in enumerate(chosen,1):
  text=r[3]; assert len(text)==int(r[0]) and all(c in bychar for c in text)
  # 保留原句的标点边界，不把逗号两边合成词。
  spans=re.findall('[一-鿿]+',r[2]);assert ''.join(spans)==text
  tokens=[];readings=[];flags=[]
  for span in spans:
   i=0
   while i<len(span):
    w=wd.get(span[i:i+2])
    if w:
     token=w['词']; prefix=[w['码'][:2],w['码'][2:]]
     tokens.append(token)
     for ch,pr in zip(token,prefix):
      readings.append(pr);flags.append('词库读音' if any(c['音码']==pr for c in bychar[ch]) else '词音无对应单字音项')
     i+=2
    else:
     ch=span[i];tokens.append(ch);readings.append(bychar[ch][0]['音码']);flags.append('多音默认待核' if len(bychar[ch])>1 else '单读音');i+=1
  corpus.append({'id':n,'原行':original,'来源':r[1],'原句':r[2],'汉字':text,'词组切分':tokens,'音码':readings,'读音依据':flags})
 write(I/'固定一万句.json',corpus)
 manifest={'版本':1,'随机种子':20260912,'句数':10000,'去重文本数':len({r['汉字'] for r in corpus}),'来源':dict(Counter(r['来源'] for r in corpus)),'字次':sum(len(r['汉字']) for r in corpus),'读音依据':dict(Counter(f for r in corpus for f in r['读音依据'])),'说明':'旧10020句中固定随机抽取10000行，保留原抽样中重复文本。原抽样非自然频率分布；本语料不是全新隐藏测试集。词库为既有训练用60000二字词。'}
 manifest['sha256']={n:digest(I/n) for n in ['固定一万句.json','固定无简词词库.json','字音基准.json','当量表.tsv']};write(I/'固定清单.json',manifest)
def verify():
 for n,h in read(I/'固定清单.json')['sha256'].items():assert digest(I/n)==h,('输入已变',n)
def eqtable():
 d={}
 for line in (I/'当量表.tsv').read_text(encoding='utf-8').split('\n'):
  if line.startswith('#') or '\t' not in line:continue
  k,v=line.split('\t');
  if len(k)==2:d[k]=float(v)
 return d
EQ=eqtable()
F={' ':0}
for i,keys in enumerate(['1qaz','2wsx','3edc','45rtfgvb','67yuhjnm','8ik,','9ol.','0p;/[]\'-='],1):
 for k in keys:F[k]=i
ROW={k:i for i,s in enumerate(['1234567890-=','qwertyuiop[]',"asdfghjkl;'",'zxcvbnm,./']) for k in s}
def commit(pos):
 assert pos>=1
 return '='*((pos-1)//3)+[' ', ';', "'"][(pos-1)%3]
def analyze(streams,chars):
 keys=Counter();pairs=Counter();triple=Counter();quad=Counter()
 for s,weight in streams:
  keys.update({k:v*weight for k,v in Counter(s).items()})
  pairs.update({s[i:i+2]:v*weight for i,v in []}) if False else None
  for n,target in [(2,pairs),(3,triple),(4,quad)]:target.update({k:v*weight for k,v in Counter(s[i:i+n] for i in range(len(s)-n+1)).items()})
 count=sum(keys.values());pn=sum(pairs.values());known=sum(v for k,v in pairs.items() if k in EQ);eq=sum(EQ[k]*v for k,v in pairs.items() if k in EQ)
 fingers=Counter()
 for k,v in keys.items():fingers[F[k]]+=v
 def rate(test,counter=pairs):return sum(v for k,v in counter.items() if test(k))/max(1,sum(counter.values()))
 d={'字次':chars,'总击键':count,'每字击键':count/max(chars,1),'键对数':pn,'已知当量键对数':known,'当量覆盖率':known/max(pn,1),'已知总当量':eq,'键均当量':eq/known if known else None,'字均当量':eq/chars if known==pn and chars else None,'缺失当量键对':{k:v for k,v in pairs.items() if k not in EQ},'按键次数':dict(keys),'各指次数':dict(fingers),'同键连击率':rate(lambda k:k[0]==k[1]),'同指异键率':rate(lambda k:F[k[0]]!=0 and F[k[0]]==F[k[1]] and k[0]!=k[1]),'大跨排率':rate(lambda k:F[k[0]]!=0 and F[k[0]]==F[k[1]] and abs(ROW[k[0]]-ROW[k[1]])>=2),'小跨排率':rate(lambda k:F[k[0]]!=0 and F[k[0]]==F[k[1]] and abs(ROW[k[0]]-ROW[k[1]])==1),'同键三连率':rate(lambda k:len(set(k))==1,triple),'同键四连率':rate(lambda k:len(set(k))==1,quad),'同指三连率':rate(lambda k:F[k[0]]!=0 and len({F[x] for x in k})==1,triple),'同指四连率':rate(lambda k:F[k[0]]!=0 and len({F[x] for x in k})==1,quad)}
 nonthumb=count-fingers[0];left=sum(fingers[i] for i in range(1,5))
 d.update({'左手占比_不含空格':left/max(nonthumb,1),'小指占比_不含空格':(fingers[1]+fingers[8])/max(nonthumb,1),'最高单键占比_不含空格':max([v for k,v in keys.items() if k!=' '] or [0])/max(nonthumb,1),'最高单指占比_不含空格':max([v for k,v in fingers.items() if k] or [0])/max(nonthumb,1)})
 return d
def load_chars(path):
 # Chai五列；同码按其导出的rank排序。音码来自全码前两位。
 codes=defaultdict(list); options=defaultdict(set);order={};short=set();records=[]
 for i,line in enumerate(path.read_text(encoding='utf-8-sig').splitlines()):
  r=line.split('\t')
  if len(r)!=5:raise ValueError('需要Chai五列：字、全码、全码序号、最短码、最短码序号')
  ch,full,fr,sc,sr=r
  if len(ch)!=1:continue
  assert len(full)==4 and full.isascii() and full.isalpha() and sc.isalpha() and 1<=len(sc)<=4
  key=(ch,full[:2]);order.setdefault(key,i);records.append((key,full,sc));
  if len(sc)<4:short.add(key)
  for code,rank in [(full,int(fr)),(sc,int(sr))]:codes[code].append((rank,i,ch));options[key].add(code)
 tables={c:list(dict.fromkeys(x[2] for x in sorted(v))) for c,v in codes.items()}
 # 补三简只在无其他单字的码位加入，不改变最短输入路径。
 for key,full,sc in records:
  if len(sc)==2 and (full[:3] not in tables or tables[full[:3]]==[key[0]]):
   tables.setdefault(full[:3],[key[0]]);options[key].add(full[:3])
 return tables,options,short

def run(path,name):
 verify();out=P/'results'/name;out.mkdir(parents=True,exist_ok=True)
 words=read(I/'固定无简词词库.json');corpus=read(I/'固定一万句.json');base=read(I/'字音基准.json')
 pure,options,short=load_chars(path);mixed={c:list(v) for c,v in pure.items()};wc=defaultdict(list)
 for w in words:wc[w['码']].append(w['词'])
 for code,ws in wc.items():
  cs=pure.get(code,[]);mixed[code]=[c for c in cs if (c,code[:2]) not in short]+ws+[c for c in cs if (c,code[:2]) in short]
 for label,table in [('纯单字',pure),('无简词字词',mixed)]:
  (out/(label+'码表.txt')).write_text(''.join(f'{c}={i},{v}\n' for c,vs in sorted(table.items()) for i,v in enumerate(vs,1)),encoding='utf-8')
 words_by={w['词']:w['码'] for w in words};default={}
 for c in base:default.setdefault(c['字'],c['音码'])
 def char_option(ch,pr,table):
  opts=options.get((ch,pr))
  if not opts:return None
  return min(((c,table[c].index(ch)+1) for c in opts),key=lambda x:(len(x[0]),x[1],x[0]))
 # 冻结读音在字音集外时不跨音借简码；缺失独立计数、不删句。
 modes={}
 for mode,table in [('纯单字',pure),('无简词字词',mixed)]:
  streams=[]; coding=[];traces=[];counts=Counter();sources=defaultdict(Counter)
  for row in corpus:
   tokens=list(row['汉字']) if mode=='纯单字' else row['词组切分'];offset=0;s='';cs='';events=[]
   def emit(ch,pr):
    nonlocal s,cs
    opt=char_option(ch,pr,table)
    if opt is None:
     counts['缺字音字次']+=1;events.append({'目标':ch,'音码':pr,'缺失':True});return
    code,pos=opt;seq=code+commit(pos);s+=seq;cs+=code
    purepos=pure[code].index(ch)+1
    counts['单字上屏次数']+=1;counts['字字选重次数']+=purepos>1
    counts['词插入使字位后移次数']+=pos>purepos
    counts['词插入新增字选重次数']+=purepos==1 and pos>1
    counts['词插入新增字翻页键数']+=(pos-1)//3-(purepos-1)//3
    counts['输出字次']+=1;counts['上屏次数']+=1;counts['编码键']+=len(code);counts['选重次数']+=pos>1;counts['翻页次数']+=(pos-1)//3;counts['三码内字次']+=len(code)<=3
    counts['单字遇词同码次数']+=any(len(x)>1 for x in table[code]);events.append({'目标':ch,'码':code,'位':pos,'按键':seq})
   for token in tokens:
    prs=row['音码'][offset:offset+len(token)];offset+=len(token)
    if len(token)>1:
     code=words_by[token];pos=table[code].index(token)+1
     purewordpos=wc[code].index(token)+1
     counts['词词原有非首选尝试次数']+=purewordpos>1
     counts['词词原有超三选拆词次数']+=purewordpos>3
     counts['单字导致有效词位后移次数']+=purewordpos<=3 and pos>purewordpos
     counts['单字新增词选重次数']+=purewordpos==1 and 1<pos<=3
     counts['尝试打词次数']+=1;counts['词遇字同码次数']+=any(len(x)==1 for x in table[code]);counts['字占位导致词位后移次数']+=pos>purewordpos
     if pos<=3:
      seq=code+commit(pos);s+=seq;cs+=code;counts['输出字次']+=len(token);counts['上屏次数']+=1;counts['打词次数']+=1;counts['实际打词中词词选重次数']+=purewordpos>1;counts['选重次数']+=pos>1;counts['编码键']+=4;events.append({'目标':token,'码':code,'位':pos,'按键':seq});continue
     counts['词超三选拆单次数']+=1;counts['字占位导致拆词次数']+=purewordpos<=3
    for ch,pr in zip(token,prs):emit(ch,pr)
   streams.append((s,1));coding.append((cs,1));traces.append({'id':row['id'],'按键':s,'事件':events});sources[row['来源']]['字次']+=len(row['汉字']);sources[row['来源']]['击键']+=len(s)
  total=sum(len(r['汉字']) for r in corpus);d=analyze(streams,counts['输出字次']);d.update(counts);d.update({'目标字次':total,'选重率_每次上屏':counts['选重次数']/counts['上屏次数'],'字词碰撞率_每次上屏或尝试词':(counts['单字遇词同码次数']+counts['词遇字同码次数'])/max(1,counts['上屏次数']+counts['尝试打词次数']),'分来源':dict(sources),'编码键热力':dict(Counter(''.join(s for s,_ in coding)))})
  auditfields=['单字上屏次数','字字选重次数','词插入使字位后移次数','词插入新增字选重次数','词插入新增字翻页键数','词词原有非首选尝试次数','词词原有超三选拆词次数','单字导致有效词位后移次数','单字新增词选重次数','实际打词中词词选重次数','字占位导致拆词次数']
  d.update({k:counts[k] for k in auditfields})
  d['字字选重率_单字上屏']=counts['字字选重次数']/max(1,counts['单字上屏次数'])
  d['字词增量受影响率']=(counts['词插入使字位后移次数']+counts['单字导致有效词位后移次数'])/max(1,counts['单字上屏次数']+counts['尝试打词次数'])
  d['缺字音字次']=counts['缺字音字次'];d['可计分']=counts['缺字音字次']==0 and not d['缺失当量键对'];modes[mode]=d
  write(out/(mode+'_逐句按键.json'),traces)
 # 理论：每个字音独立输入；不拼接不同单字，按字音频率加权。
 theory=[];missing=0
 for item in base:
  opt=char_option(item['字'],item['音码'],pure)
  if opt is None:missing+=item['频率'];continue
  code,pos=opt;theory.append((code+commit(pos),item['频率']))
 theoretical=analyze(theory,sum(w for _,w in theory));theoretical['缺字音频次']=missing
 result={'组别':name,'单字表SHA256':digest(path),'固定输入':read(I/'固定清单.json'),'理论当量_统一46键表':theoretical,'实战':modes}
 write(out/'结果.json',result);print(name,[(k,v['缺字音字次'],round(v['每字击键'],4)) for k,v in modes.items()],flush=True)
 return result
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--table',type=Path);ap.add_argument('--name');ap.add_argument('--all',action='store_true');args=ap.parse_args();freeze()
 if args.all:
  for r in read(A/'manifest.json')['results']:run(Path(r['output'])/'code.txt',r['id'])
 elif args.table:run(args.table,args.name or args.table.stem)
