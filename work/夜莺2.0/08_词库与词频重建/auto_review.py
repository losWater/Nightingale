from pathlib import Path
from collections import defaultdict,Counter
import json,runpy,re,hashlib,random
O=Path(__file__).resolve().parent
old=runpy.run_path(str(O.parent/'03_字音频率审计/rebuild.py'));dc=old['double_code'];norm=old['syllable']
allowed=defaultdict(set)
for r in old['table'](old['BASE']):allowed[r['汉字']].add(r['拼音'])
def valid(w,py):
 p=py.split()
 return len(p)==len(w) and all(re.fullmatch('[a-z]+',s) and dc(s) for s in p)
def decode(w,code):
 if len(code)!=2*len(w):return None
 opts=[{s for s in allowed[c] if dc(s)==code[2*i:2*i+2]} for i,c in enumerate(w)]
 return ' '.join(next(iter(x)) for x in opts) if all(len(x)==1 for x in opts) else None
def decide(r):
 w=r['词'];e={k:set(v) for k,v in r['读音证据'].items() if k!='墨奇双拼'}
 decoded={x for code in r['读音证据'].get('墨奇双拼',[]) if (x:=decode(w,code))}
 if decoded:e['墨奇整词还原']=decoded
 e={k:{x for x in v if valid(w,x)} for k,v in e.items()};e={k:v for k,v in e.items() if v}
 allpy=set().union(*e.values()) if e else set()
 if len(allpy)>1 and r['读音状态']!='已人工裁定':
  return '多读音证据待核',None,'保留全部来源读音，不用多数票抹去可能的异义读音，也不分摊词频',sorted(allpy)
 if r['采用拼音']:return '沿用通过',r['采用拼音'],'首轮通过或既有人工裁决',sorted(allpy-{r['采用拼音']})
 # Two corpus sources plus dictionary, or three evidence families; reference extras never gain separate votes.
 scored=[]
 for py in allpy:
  corpus=sum(py in e.get(k,set()) for k in ['CLD整词','SUBTLEX整词'])
  dictionaries=sum(py in e.get(k,set()) for k in ['Chai整词','墨奇整词还原'])
  he=any(py in e.get(k,set()) for k in ['简单鹤','鲸凉鹤'])
  families=(corpus>0)+(dictionaries>0)+he
  if (corpus==2 and dictionaries>=1) or (families==3 and dictionaries==2):
   scored.append((corpus+dictionaries+int(he),py))
 scored.sort(reverse=True)
 if scored and (len(scored)==1 or scored[0][0]>scored[1][0]):
  py=scored[0][1]
  return '自动确定主读',py,'跨类型整词证据占优；其他读音仅留审计，不自动作为合法容错',sorted(allpy-{py})
 # Monophonic spelling only when every character has exactly one audited reading; never choose polyphonic defaults.
 if all(len(allowed[c])==1 for c in w):
  py=' '.join(next(iter(allowed[c])) for c in w)
  if valid(w,py) and (not allpy or allpy=={py}):return '单音字组合通过',py,'各字在已审计读音集合内均为单音；没有整词反证',[]
 if len(allpy)==1:
  py=next(iter(allpy))
  # One dictionary family is enough for provisional extension, not enough for core auto-certification.
  return '扩展词待验证',py,'只有单类整词证据；可供扩展候选，暂不纳入核心',[]
 return '仍需消歧',None,'整词证据分歧或缺证',sorted(allpy)
def main():
 stats=Counter();pending=[];samples=defaultdict(list);rng=random.Random(20260912);n=0;top10=0
 paths={k:(O/v).open('w',encoding='utf-8') for k,v in {'all':'二字词60000_自动分流.jsonl','core':'可用二字词_自动核对.jsonl','extension':'扩展及缺证候选.jsonl'}.items()}
 for line in (O/'二字词前60000_候选.jsonl').open(encoding='utf-8'):
  r=json.loads(line);status,py,reason,alternatives=decide(r)
  r.update(词条质量说明='读音候选；词条质量未逐词审定',单一语料来源=r['语料家族覆盖']<2)
  r.update(处理分类=status,主读音=py,处理依据=reason,其他读音证据=alternatives,主读双拼=''.join(dc(x) for x in py.split()) if py else None)
  assert not py or valid(r['词'],py)
  if status in ['沿用通过','自动确定主读','单音字组合通过']:
   dest='core'
  else:
   dest='extension'
   if r['二字词排名']<=10000:pending.append(r);top10+=1
  text=json.dumps(r,ensure_ascii=False)+'\n';paths['all'].write(text);paths[dest].write(text);stats[status]+=1;n+=1
  # Reproducible reservoirs for sampling, plus all top-ranked auto decisions.
  bucket=samples[status]
  if len(bucket)<30:bucket.append(r)
  else:
   i=rng.randrange(stats[status])
   if i<30:bucket[i]=r
 for f in paths.values():f.close()
 assert n==60000
 (O/'高频人工队列.json').write_text(json.dumps(pending,ensure_ascii=False,indent=2),encoding='utf-8')
 (O/'自动处理抽样.json').write_text(json.dumps(samples,ensure_ascii=False,indent=2),encoding='utf-8')
 summary={'原待核':14998,'处理分类':dict(stats),'自动新增通过':stats['自动确定主读']+stats['单音字组合通过'],'原通过转待核':45002-stats['沿用通过'],'读音通过候选总数':stats['沿用通过']+stats['自动确定主读']+stats['单音字组合通过'],'前10000未自动通过':top10,'说明':'候选主读音不等于读音频率占比；其他读音证据不自动判作合法容错。未修改发布表及旧字频。'}
 (O/'自动分流摘要.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=False));print('高频剩余',[(r['词'],r['二字词排名'],r['读音证据']) for r in pending[:25]])
if __name__=='__main__':main()
