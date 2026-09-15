from pathlib import Path
import json,csv,re,runpy,collections,html
P=Path(__file__).resolve().parent;W=P.parent;mod=runpy.run_path(str(W/'03_字音频率审计/rebuild.py'));dc=mod['double_code'];mod['FLY'][('道','jf')]='dc';allowed=collections.defaultdict(set)
with mod['BASE'].open(encoding='utf-8-sig') as f:
 for r in csv.DictReader(f,delimiter='\t'):
  k=dc(r['拼音'])
  if k:allowed[r['汉字']].add(k)
pairs=dict((b,a) for a,b in re.findall(r'derive/([a-z]{2});/([a-z]{2});/',(W/'56_鲸凉鹤原词库字词版/WhaleCold_defs.yaml').read_text(encoding='utf-8')))
policy=runpy.run_path(str(W/'56_鲸凉鹤原词库字词版/restore_fly.py'));restore=policy['restore'];allowed=policy['allowed']
words=collections.defaultdict(set);lines=collections.defaultdict(list)
for no,l in enumerate(mod['JL'].read_text(encoding='utf-8-sig').splitlines(),1):
 m=re.fullmatch(r'([a-z]{4})=\d+,(..)',l)
 if not m:continue
 k,w=m.groups();nk=''.join(restore(c,k[2*i:2*i+2]) for i,c in enumerate(w));words[w].add(nk);lines[w,nk].append({'原码':k,'行':no})
sus=[];groups=collections.defaultdict(list)
for w,ks in words.items():
 good=[k for k in ks if all(k[2*i:2*i+2] in allowed[c] for i,c in enumerate(w))]
 for k in sorted(ks):
  bad=[{'字':c,'码':k[2*i:2*i+2],'已知音码':sorted(allowed[c])} for i,c in enumerate(w) if k[2*i:2*i+2] not in allowed[c]]
  if not bad:continue
  r={'词':w,'待核码':k,'正常音码候选':sorted(good),'异常音节':bad,'来源':lines[w,k]};sus.append(r)
  for b in bad:groups[b['字'],b['码']].append(r)
ranked=[]
for (c,k),rs in groups.items():
 suggestions=collections.Counter()
 for r in rs:
  for target in r['正常音码候选']:
   for i,ch in enumerate(r['词']):
    if ch==c and r['待核码'][2*i:2*i+2]==k:suggestions[target[2*i:2*i+2]]+=1
 ranked.append({'字':c,'待核音码':k,'涉及词数':len(rs),'同词正常版本指向':dict(suggestions),'示例':[r['词'] for r in rs[:8]]})
ranked.sort(key=lambda r:-r['涉及词数'])
for name,data in [('待核二字词',sus),('疑似飞键分组',ranked)]: (P/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('二字词',len(words),'待核词码',len(sus),'涉及词',len({r['词'] for r in sus}),'分组',len(ranked));print(json.dumps(ranked[:25],ensure_ascii=False));print('烟道',[r for r in sus if r['词']=='烟道'])
