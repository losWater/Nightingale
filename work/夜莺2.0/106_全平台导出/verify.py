from pathlib import Path
from collections import defaultdict
import json,re,csv,subprocess,shutil,os
P=Path(__file__).resolve().parent;O=P/'夜莺2.0_字词表与输入法'
def rows(p,enc='utf-8-sig'):return [x.split('\t') for x in p.read_text(encoding=enc).splitlines() if x]
base=rows(P.parent/'113_扩展字入表/夜莺2.0最终表_普通格式.txt')
normal=rows(O/'普通字词表/夜莺2.0_有简词_普通.txt');assert normal==base
assert rows(O/'普通字词表/夜莺2.0_有简词_码前.txt')==[r[::-1] for r in base]
ns=rows(O/'普通字词表/夜莺2.0_无简词_普通.txt')
assert ns==[r for r in base if not(len(r[1])<4 and len(r[0])>1 and (sum('\u3400'<=x<='\u9fff' for x in r[0])<4 or r[0].startswith('$ddcmd(')))]
assert ['说道：“','ud'] not in ns
assert rows(O/'普通字词表/夜莺2.0_无简词_码前.txt')==[r[::-1] for r in ns]
g=defaultdict(list)
for t,c in base:g[c].append(t)
quick=[]
for s in (P/'参考模板/快符原表.txt').read_text(encoding='utf-8-sig').splitlines():
 m=re.fullmatch('([a-z]+),(\d+)=(.+)',s)
 if m:
  c,n,t=m.groups();n=int(n);quick.append((t,c))
  if t not in g[c]:g[c].insert(n-1,t)   # 与生成脚本一致：彳亍 xing 已在最终表中，不重复插入
expected={(t,c,n) for c,ts in g.items() for n,t in enumerate(ts,1) if not t.startswith('$ddcmd(')}
mod=[]
for p in (O/'手心/模块化挂接').glob('*.txt'):
 for s in p.read_text(encoding='utf-8-sig').splitlines():
  c,tail=s.split('=',1);n,t=tail.split(',',1);mod.append((t,c,int(n)))
assert len(mod)==len(set(mod)) and set(mod)==expected
sg=[]
for s in (O/'搜狗挂接/夜莺2.0_挂接_含快符.txt').read_text(encoding='utf-16').splitlines():
 head,t=s.split('=',1);c,n=head.split(',');sg.append((t,c,int(n)))
assert len(sg)<=100000 and set(sg)=={r for r in expected if not(len(r[0])==2 and len(r[1])==4 and (r[0],r[1]) not in quick)}
wb=rows(O/'搜狗五笔/夜莺2.0_五笔_含快符.txt');assert len(wb)<=200000
wbset={(t,c) for c,t in wb}
assert {(t,c) for t,c in base if len(t)==1}|set(quick)<=wbset
assert {(t,c) for t,c in base if len(c)<4 and not t.startswith('$ddcmd(')}<=wbset
for c,ts in json.loads((P.parent/'64_加入鲸凉鹤简词/码位人工指定.json').read_text(encoding='utf-8-sig')).items():assert {(t,c) for t in ts if (t,c) in set(map(tuple,base))}<=wbset   # 只查仍在最终表中的人工指定项（旧指定里有已删词/简码位条目）
wg=defaultdict(list)
for c,t in wb:wg[c].append(t)
assert all(ts==[t for t in g[c] if (t,c) in wbset] for c,ts in wg.items())
valid={r for r in expected if len(r[1])<=4}
bm=rows(O/'Bime/mb/夜莺2.0/夜莺字词.txt');assert {(t,c,100000-int(n)) for t,c,n in bm}==valid
ice=(O/'冰凌五笔/夜莺2.0_词库_含快符.txt').read_text(encoding='utf-16').split('[CODETABLE]\n',1)[1]
assert {(t,c,10000-int(n)) for c,t,n in [x.split('\t') for x in ice.splitlines()]}==valid
aux=(O/'手心/夜莺2.0_辅助码.txt').read_text(encoding='utf-8')
assert aux==(O/'手心/夜莺2.0_辅助码_Unicode.txt').read_text(encoding='utf-16')
a={t:set(cs.split()) for t,cs in [s.split('=',1) for s in aux.splitlines()]}
b=defaultdict(set)
for t,c in base:
 if len(t)==1 and len(c)==4:b[t].add(c[2:])
assert a==b
for label in ['轻量版','主力版']:
 p=P/f'Rime_{label}'
 ss=(p/'yeying20_rime_fixed.dict.yaml').read_text(encoding='utf-8').split('...\n',1)[1]
 assert {(t,c,100000-int(n)) for t,c,n in [l.split('\t') for l in ss.splitlines()]}==expected
 assert 'yeying_lookup_data' not in (p/'lua/yeying20_lookup.lua').read_text(encoding='utf-8')
result={'全格式与候选核验':'通过','含简词':len(base),'无简词':len(ns),'手心含快符':len(mod),'搜狗挂接':len(sg),'搜狗五笔':len(wb),'冰凌及Bime':len(bm),'Rime固定条目':len(expected)}
(P/'数据核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(result,flush=True)
# Use an unused ASCII drive alias for the inherited Windows native engine.
drive=next(x for x in 'RSTUVW' if not Path(x+':/').exists())+':'
subprocess.run(['subst',drive,str(P)],check=True)
cases=['bb','dr','hu','ji','pk','rv','so','ty','ud','uu','jv','jvb','jvn','jvo','xv','yv','yvl','yvz','yvc','yvo','vgss','yjs','yjsp','qtxb','a','q','no','xing']
longcode=next(c for c in g if len(c)>4);cases.append(longcode)
try:
 for kind,label,schema in [('light','轻量版','yeying20_light'),('main','主力版','yeying20_main'),('mobile','手机版','yeying20_light')]:
  dest=P/'engine-check-final'/kind
  def copy(src,dst):
   if str(src).endswith(('.bin','.gram')):os.link(src,dst)
   else:shutil.copy2(src,dst)
  shutil.copytree(P/f'Rime_{label}',dest,copy_function=copy,dirs_exist_ok=False)
  assert (dest/'default.custom.yaml').exists() and not (dest/'default.custom.yaml.example').exists()   # 包内直接带生效配置
  codes=cases+['woxihrni','wobuvidc','~zheng','`vg']
  with (P/f'{kind}-engine.tsv').open('wb') as out,(P/f'{kind}-engine.log').open('wb') as err:
   proc=subprocess.run(['D:/nightingale/.tmp/rime_bench.exe','D:/Rime/weasel-0.17.4','D:/Rime/weasel-0.17.4/data',drive+'/engine-check-final/'+kind,schema,'maintenance'],input=('\n'.join(codes)+'\n').encode(),stdout=out,stderr=err,timeout=240)
  assert proc.returncode==0,(kind,proc.returncode)
  actual=rows(P/f'{kind}-engine.tsv','utf-8');assert len(actual)==len(codes)
  for line in actual[:len(cases)]:
   c=line[0];assert line[3:3+min(len(g[c]),3)]==g[c][:3],(kind,c,line,g[c][:3])
  assert '正' in actual[-1][3:] and '正' in actual[-2][3:],actual[-2:]
  result[kind]={'引擎':'小狼毫0.17.4独立部署通过','固定候选抽检':len(cases),'反查':'通过','整句样例':[r[0:1]+r[3:] for r in actual[-4:-2]]}
  print(kind,'PASS',flush=True)
finally:subprocess.run(['subst',drive,'/D'],check=True)
(P/'引擎核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
