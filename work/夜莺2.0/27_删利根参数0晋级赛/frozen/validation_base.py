from pathlib import Path
from collections import Counter,defaultdict
import json,yaml,subprocess,concurrent.futures,random,statistics,math,re,copy,time
O=Path(__file__).resolve().parent;P=O.parent
exe=Path('E:/nightingale2-build/release/chai.exe')
manifest=json.loads((O/'manifest.json').read_text(encoding='utf-8'))
configs={c['id']:yaml.safe_load((Path(c['directory'])/'config.yaml').read_text(encoding='utf-8')) for c in manifest['cards']}
elements={n:yaml.safe_load((O/n).read_text(encoding='utf-8')) for n in ['elements.yaml','elements_ji_ju.yaml']}
def execute(cfg,where,elem,mode='encode'):
 where.mkdir(exist_ok=True,parents=True);path=where/'run.json'
 previous=sorted(where.glob('output-*/metric.json'))
 if previous and path.exists() and json.loads(path.read_text(encoding='utf-8'))==cfg:
  out=previous[-1].parent
  return out,json.loads(previous[-1].read_text(encoding='utf-8'))
 path.write_text(json.dumps(cfg,ensure_ascii=False),encoding='utf-8')
 cmd=[str(exe),mode,str(path),'-e',str(O/elem),'-k',str(O/'distribution.txt'),'-p',str(O/'equivalence.txt')]
 if mode=='optimize':cmd+=['-t','1']
 r=subprocess.run(cmd,cwd=where,capture_output=True,encoding='utf-8',errors='replace')
 (where/'stdout.log').write_text(r.stdout,encoding='utf-8');(where/'stderr.log').write_text(r.stderr,encoding='utf-8')
 assert r.returncode==0,(str(where),r.stderr)
 outputs=sorted(where.glob('output-*'));out=outputs[-1]
 metric=json.loads((out/'metric.json').read_text(encoding='utf-8'))
 return out,metric

def validate(out,elem):
 es=elements[elem];lines=[l.split('\t') for l in (out/'code.txt').read_text(encoding='utf-8').splitlines()]
 assert len(es)==len(lines)
 fullspace=Counter(r[1] for r in lines);shortspace=Counter();expected={}
 for i,(e,r) in enumerate(zip(es,lines)):
  assert e['词']==r[0] and len(r)==5
  if '简码长度' in e:
   slot=r[1][:e['简码长度']];expected[i]=slot;shortspace[slot]+=1
 for i,(e,r) in enumerate(zip(es,lines)):
  if i in expected:continue
  code=r[1];slot=code
  if len(e['词'])==1:
   for n in [1,2,3]:
    if len(code)>n and fullspace[code[:n]]+shortspace[code[:n]]<1:
     slot=code[:n];break
  expected[i]=slot;shortspace[slot]+=1
 for i,r in enumerate(lines):assert r[3]==expected[i],(i,r,expected[i])
 groups=defaultdict(list)
 for i,r in enumerate(lines):groups[r[1]].append(i)
 for code,indices in groups.items():
  ordered=sorted(indices,key=lambda i:(lines[i][3]!=code,i))
  for rank,i in enumerate(ordered):assert int(lines[i][2])==rank,(code,lines[i],rank)
 # Extra third-code entries only after all primary single-character slots have been assigned.
 occupied={r[3] for r in lines if len(r[0])==1}
 extras=[]
 for r in lines:
  if len(r[0])==1 and len(r[3])==2 and r[1][:3] not in occupied:
   extras.append({'字':r[0],'二简':r[3],'补三简':r[1][:3]});occupied.add(r[1][:3])
 (out/'二简补三简.json').write_text(json.dumps(extras,ensure_ascii=False,indent=2),encoding='utf-8')
 freq=[int(e['频率']) for e in es if len(e['词'])==1];chars=lines[:len(freq)]
 total=sum(freq);bylen=Counter(len(r[3]) for r in chars)
 def coverage(n):return sum(f for f,r in zip(freq,chars) if len(r[3])<=n and int(r[4])==0)/total
 return {'字音项':len(chars),'最短码长分布':dict(bylen),'三码及以内首选字频覆盖':coverage(3),'三码及以内首选项数':sum(len(r[3])<=3 and int(r[4])==0 for r in chars),'补三简入口':len(extras),'锁定及占位校验':'通过'}

starts=[]
for c in manifest['cards']:
 out,metric=execute(configs[c['id']],Path(c['directory'])/'initial',c['elements'])
 v=validate(out,c['elements']);starts.append((c,out,metric,v));print('INITIAL',c['id'],metric['score'],flush=True)
# Calibrate temperature from actual single-group loss changes at projection and random starts.
deltas=[]
for j in [0,2]:
 c,_,metric,_=starts[j];cfg0=configs[c['id']];rr=random.Random(1900+j)
 for i in range(6):
  cfg=copy.deepcopy(cfg0);g=rr.choice(list(manifest['group_names']));k=rr.choice('abcdefghijklmnopqrstuvwxyz')
  cfg['form']['mapping'][g]=k
  out,met=execute(cfg,O/'calibration'/f'{j}_{i}',c['elements'])
  deltas.append(met['score']-metric['score'])
nonzero=[abs(d) for d in deltas if abs(d)>1e-9]
tmax=statistics.median(nonzero)/(-math.log(.65));tmin=tmax/1000
(O/'temperature.json').write_text(json.dumps({'loss_deltas':deltas,'t_max':tmax,'t_min':tmin,'method':'median absolute one-group loss difference; 65% acceptance at that scale; 12 probes, provisional'},indent=2),encoding='utf-8')
print('TEMPERATURE',tmax,tmin,flush=True)

def run(start):
 c,initial,im,iv=start;cfg=configs[c['id']]
 cfg['optimization']['metaheuristic']['parameters']={'t_max':tmax,'t_min':tmin,'steps':3000}
 out,metric=execute(cfg,Path(c['directory'])/'short_run',c['elements'],'optimize')
 v=validate(out,c['elements'])
 stderr=(out.parent/'stderr.log').read_text(encoding='utf-8')
 match=re.search(r'TRIAL_CACHE_DELTA ([^\s]+)',stderr);assert match,stderr
 delta=float(match[1]);assert delta<1e-7,(c['id'],delta)
 # Native saved final configuration is located by reading its emitted YAML files.
 candidates=list(out.glob('*.yaml'))
 finals=[p for p in candidates if p.name in ['config.yaml','solution.yaml']]
 if not finals:finals=sorted([p for p in candidates if p.name.startswith('solution')])[-1:]
 assert finals,[p.name for p in candidates]
 finalcfg=yaml.safe_load(finals[0].read_text(encoding='utf-8'))
 finalcfg['generated_mapping_space']=cfg['generated_mapping_space']
 vo,vm=execute(finalcfg,Path(c['directory'])/'verify',c['elements']);validate(vo,c['elements'])
 assert abs(vm['score']-metric['score'])<1e-7,(vm['score'],metric['score'])
 changes=sum(cfg['form']['mapping'][g]!=finalcfg['form']['mapping'][g] for g in manifest['group_names'])
 result={'id':c['id'],'kind':c['kind'],'initial_score':im['score'],'final_score':metric['score'],'initial':iv,'final':v,'changed_groups':changes,'cache_delta':delta,'acceptance':re.search(r'TRIAL_ACCEPT .*',stderr).group(0),'output':str(out),'final_config':str(finals[0])}
 print('DONE',c['id'],result['final_score'],changes,flush=True)
 return result
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,starts))
manifest['status']='short_run_complete';manifest['results']=results
(O/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('ALL_COMPLETE',flush=True)
