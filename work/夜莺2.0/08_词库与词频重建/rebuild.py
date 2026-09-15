from pathlib import Path
from collections import defaultdict,Counter
import json,csv,runpy,re,math,hashlib
O=Path(__file__).resolve().parent;S=O/'来源快照';ROOT=O.parents[2]
old=runpy.run_path(str(O.parent/'03_字音频率审计/rebuild.py'));dc=old['double_code'];norm=old['syllable']
def table(p):
 with p.open(encoding='utf-8-sig',newline='') as f:yield from csv.DictReader(f,delimiter='\t' if p.suffix=='.tsv' else ',')
def valid(w):return 2<=len(w)<=10 and all('\u3400'<=c<='\u9fff' for c in w)
allowed=defaultdict(set)
for r in old['table'](old['BASE']):allowed[r['汉字']].add(r['拼音'])
refs=defaultdict(lambda:defaultdict(set));frequency={};candidates=set();fly=[];invalid=[]
for label,path,palm in [('简单鹤',old['JD'],False),('鲸凉鹤',old['JL'],True)]:
 data,err,fl=old['read_reference'](path,palm,allowed);fly+=fl;invalid+=err
 for w,readings in data.items():refs[w][label].update(' '.join(t) for t in readings);candidates.add(w)
for line in old['LEX'].read_text(encoding='utf-8-sig').splitlines():
 q=line.split('\t')
 if len(q)>1 and valid(q[0]) and len(q[1].split())==len(q[0]):refs[q[0]]['Chai整词'].add(' '.join(norm(x) for x in q[1].split()))
for line in (S/'moqi_derived.txt').open(encoding='utf-8-sig'):
 q=line.rstrip('\n').split('\t')
 if len(q)<2 or not valid(q[0]):continue
 chunks=q[1].split()
 if len(chunks)!=len(q[0]):continue
 # Derived dictionary has double pinyin, not independent full-pinyin evidence.
 code=''.join(x.split(';')[0] for x in chunks)
 if re.fullmatch('[a-z]{'+str(len(q[0])*2)+'}',code):refs[q[0]]['墨奇双拼'].add(code)
for name in ['bcc_balanced','bcc_dialogue','bcc_news','bcc_literature']:
 data=defaultdict(float)
 for r in table(S/(name+'.csv')):
  if valid(r['token']):data[r['token']]+=float(r['count'])
 frequency[name]=dict(data);candidates.update(data)
data=defaultdict(float)
for r in json.loads((S/'subtlex.json').read_text(encoding='utf-8'))['data']:
 if valid(r['Word']):data[r['Word']]+=float(r['WCount'])
frequency['subtlex']=dict(data);candidates.update(data)
data=defaultdict(float)
for r in table(S/'cld.csv'):
 w=r['Word']
 if not valid(w):continue
 try:v=float(r['FrequencyRawWeibo'])
 except ValueError:v=0
 if v>0:data[w]+=v
 ps=[norm(r.get('C'+str(i)+'Pinyin','')) for i in range(1,len(w)+1)]
 if len(w)<=4 and all(re.fullmatch('[a-z]+',x) and x!='na' for x in ps):refs[w]['CLD整词'].add(' '.join(ps))
frequency['cld_weibo']=dict(data);candidates.update(data)
# SUBTLEX pronunciation fields retain contradictions rather than selecting first reading.
for r in old['table'](old['RAW']):
 w=r.get('Word','')
 if not valid(w):continue
 opts=old['options'](r['Pinyin'])
 if len(opts)==len(w) and all(len(x)==1 for x in opts):refs[w]['SUBTLEX整词'].add(' '.join(next(iter(x)) for x in opts))
paper={}
for name in ['paper_two.tsv','paper_mixed.tsv']:
 for r in table(S/name):
  w=r['word'];candidates.add(w)
  if w not in paper or int(r['rank'])<paper[w]:paper[w]=int(r['rank'])
current=defaultdict(set)
for line in (ROOT/'releases/v1.0/01_正式码表/夜莺1.0字词表_码前.txt').read_text(encoding='utf-8-sig').splitlines():
 q=line.split('\t')
 if len(q)==2 and len(q[1])==2 and re.fullmatch('[a-z]{4}',q[0]):current[q[1]].add(q[0]);candidates.add(q[1])
manual=json.loads(old['OVERRIDES'].read_text(encoding='utf-8'))
# Existing reviewed decisions take precedence; decode full word only against explicit reading inventory.
for r in old['table'](old['PREVIOUS']):
 w,code=r['词'],r['新码'];ps=[{s for s in allowed[ch] if dc(s)==code[2*i:2*i+2]} for i,ch in enumerate(w)]
 if all(len(x)==1 for x in ps):manual.setdefault(w,{'syllables':[next(iter(x)) for x in ps]})
totals={k:sum(v.values()) for k,v in frequency.items()};ranks={}
for k,v in frequency.items():ranks[k]={w:i for i,(w,_) in enumerate(sorted(v.items(),key=lambda x:(-x[1],x[0])),1)}
def rankscore(k,w):
 r=ranks[k].get(w)
 return None if r is None else 1-math.log(r)/math.log(len(ranks[k])+1)
def resolve(w):
 rr=refs[w];explicit={k:set(v) for k,v in rr.items() if k!='墨奇双拼'}
 if w in manual:return '已人工裁定',' '.join(manual[w]['syllables']),explicit
 candidates=set().union(*explicit.values()) if explicit else set()
 if len(candidates)!=1:return ('多读音或来源分歧' if candidates else '缺少整词读音'),' ',explicit
 py=next(iter(candidates));parts=py.split();code=''.join(dc(s) or '?' for s in parts)
 if len(parts)!=len(w) or '?' in code:return '读音格式待核',' ',explicit
 if rr.get('墨奇双拼') and code not in rr['墨奇双拼']:return '与墨奇双拼分歧',' ',explicit
 # Count reference family once; corpus families separately. Chai/Moqi treated as dictionary family.
 families=set('鹤系' if k in ['简单鹤','鲸凉鹤'] else '词典' if k=='Chai整词' else k for k,v in explicit.items() if py in v)
 if rr.get('墨奇双拼') and code in rr['墨奇双拼']:families.add('词典')
 if len(families)<2:return '单类证据待核',' ',explicit
 return '多类证据一致',py,explicit
rows=[];stats=Counter();fixes=[];training={r['word']:r['code4'] for r in table(S/'paper_training.tsv')}
for w in sorted(candidates):
 if not valid(w):continue
 counts={k:v[w] for k,v in frequency.items() if w in v}
 # Three families equal weight; BCC domains max prevents repeated votes. Scores are ranking indexes, not measured frequencies.
 bcc=[rankscore(k,w) for k in frequency if k.startswith('bcc_') and w in ranks[k]]
 scores={'BCC':max(bcc) if bcc else None,'字幕':rankscore('subtlex',w),'微博':rankscore('cld_weibo',w)}
 score=sum(v if v is not None else 0 for v in scores.values())/3
 status,py,ev=resolve(w);py=py.strip();code=''.join(dc(s) or '?' for s in py.split()) if py else None
 record={'词':w,'词长':len(w),'排序指数':round(score,8),'语料家族覆盖':sum(v is not None for v in scores.values()),'各源原始词频':counts,'各源排名':{k:ranks[k][w] for k in counts},'来源缺失':[k for k in frequency if k not in counts],'读音状态':status,'采用拼音':py or None,'双拼全码':code,'读音证据':{k:sorted(v) for k,v in refs[w].items()},'1.0四码':sorted(current.get(w,())),'论文训练码':training.get(w)}
 rows.append(record);stats[status]+=1
 if code and len(w)==2:
  if current.get(w) and code not in current[w]:fixes.append({'词':w,'对象':'1.0历史表','旧码':sorted(current[w]),'建议码':code,'拼音':py,'依据':status})
  if w in training and code!=training[w]:fixes.append({'词':w,'对象':'论文训练表','旧码':[training[w]],'建议码':code,'拼音':py,'依据':status})
rows.sort(key=lambda r:(-r['排序指数'],-r['语料家族覆盖'],r['词']))
for i,r in enumerate(rows,1):r['综合排名']=i
byword={r['词']:r for r in rows}
fixes.sort(key=lambda r:byword[r['词']]['综合排名'])
for name,items in [('综合词表_审计候选.jsonl',rows),('读音通过_候选.jsonl',[r for r in rows if r['采用拼音']]),('待核读音.jsonl',[r for r in rows if not r['采用拼音']])]:
 with (O/name).open('w',encoding='utf-8') as f:
  for r in items:f.write(json.dumps(r,ensure_ascii=False)+'\n')
(O/'明确读音差异.json').write_text(json.dumps(fixes,ensure_ascii=False,indent=2),encoding='utf-8')
(O/'飞键处理明细.json').write_text(json.dumps({'已还原':fly,'不可解析':invalid},ensure_ascii=False,indent=2),encoding='utf-8')
examples=[byword[w] for w in ['没有','睡觉','觉得','曝光','一样','异样','一定','已定','五百','伍佰','一个','夜莺'] if w in byword]
summary={'词条数':len(rows),'状态计数':stats,'差异数':dict(Counter(x['对象'] for x in fixes)),'来源原始计数总和':totals,'飞键还原数':len(fly),'参考码待核数':len(invalid),'说明':'候选综合排名，不是实测统一词频。三大家族等权为初始假设，缺失不等于真实零频；不按参考票数自动消除异读，不分摊整词频率。不发布、不改动现行字频及1.0。','案例':examples}
(O/'审计摘要.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
md=['# 词库与词频重建：首轮审计','','本轮产物是待验证候选，未接入退火，也未改动1.0或当前字频。','','## 结果','',f'词条{len(rows):,}；读音状态：{dict(stats)}；明确差异：{summary["差异数"]}。','','## 已确认的生成问题','','论文训练表由单字码表逐字取码，不是整词注音；例如没有出现moyz。此类实验词码不能作为正确读音来源。','旧排序混入词库收录及分词词典权重；BCC子库并非独立票。本轮保留原始各源计数，BCC合为一家族。','','## 候选规则','','BCC、字幕、微博各占三分之一；各源用对数排名归一化，BCC子库取最大证据。此为待校准的排序指数，不是实际使用概率；源缺失单独列出。输入法词库不参与抬高词频。','整词读音：保留已人工裁定；其余要求显式整词拼音无分歧且至少两类证据支持。简单鹤与鲸凉鹤按一家族计；Chai和墨奇保守按词典一家族计。多个合法读音与来源冲突全部待核，不把整词频率重复分配到多个读音。','飞键只按已有逐字映射还原，未知飞键不猜。三字以上四码缩写不反解成逐字拼音。','','## 重点案例','','| 词 | 新排名 | 读音状态 | 采用拼音 | 双拼 |','|---|---:|---|---|---|']
for r in examples:md.append('| '+' | '.join(str(r[k] or '待核') for k in ['词','综合排名','读音状态','采用拼音','双拼全码'])+' |')
md+=['','## 读音修正建议前30条','','| 词 | 对象 | 原码 | 建议码 |','|---|---|---|---|']
for r in fixes[:30]:md.append('| '+r['词']+' | '+r['对象']+' | '+','.join(r['旧码'])+' | '+r['建议码']+' |')
md+=['','## 尚不能定稿的部分','','异读词需要区分语义，来源一致也不能证明某个读音占全部频率。综合排序需用未参与构建的日常文本和人工常用词对校验；现有论文测试集的词码及切分建立在旧错码上，修正后需重建，不能沿用原评测结论。','没有把这批候选自动替换现行频率。下一步优先复核高频待核词，再校准口语与书面语权重；必须通过保留测试集后再接入2.0退火。']
(O/'词库审计说明.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='案例'},ensure_ascii=False));print('examples',[(r['词'],r['综合排名'],r['采用拼音'],r['双拼全码']) for r in examples])
