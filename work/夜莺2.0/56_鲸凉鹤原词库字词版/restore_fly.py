from pathlib import Path
import collections,csv,json,re,runpy
P=Path(__file__).resolve().parent;W=P.parent
m=runpy.run_path(str(W/'03_字音频率审计/rebuild.py'));allowed=collections.defaultdict(set)
with m['BASE'].open(encoding='utf-8-sig') as f:
 for r in csv.DictReader(f,delimiter='\t'):
  k=m['double_code'](r['拼音'])
  if k:allowed[r['汉字']].add(k)
for r in json.loads((W/'54_补删鹿旁保留羊南心四起点试跑/frozen/字音基准.json').read_text(encoding='utf-8')):allowed[r['字']].add(r['音码'])
allowed['嗯'].add('en') # 用户确认的补充读音，不分配频率
fly={**m['FLY'],('道','jf'):'dc',('之','vp'):'vi',('打','dw'):'da',('几','je'):'ji',('起','qe'):'qi',('向','xj'):'xl'}
pairs=dict((b,a) for a,b in re.findall(r'derive/([a-z]{2});/([a-z]{2});/',(P/'WhaleCold_defs.yaml').read_text(encoding='utf-8')))
def restore(c,k):
 if (c,k) in fly:return fly[c,k]
 # A legitimate reading such as 拽vk or 耨nz must not be rewritten.
 if k in allowed[c]:return k
 return pairs.get(k,k)
