from pathlib import Path
import json,yaml,subprocess,psutil,time,hashlib,html,shutil,os,re,concurrent.futures,threading
O=Path(__file__).resolve().parent;W=O.parent;F=W/'27_删利根参数0晋级赛/frozen';seed=202609121701;guard=threading.Lock()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def run(mode,cfg,el,d):
 d.mkdir(parents=True,exist_ok=True);write(d/'run.json',cfg)
 cmd=[str(O/'chai-seeded.exe'),mode,str(d/'run.json'),'-e',str(el),'-k',str(F/'distribution.txt'),'-p',str(F/'equivalence.txt')]
 if mode=='optimize':cmd+=['-t','1']
 env=dict(os.environ,NIGHTINGALE_TRIAL_SEED=str(seed));assert psutil.virtual_memory().available>3*2**30
 with (d/'stdout.log').open('w',encoding='utf-8') as a,(d/'stderr.log').open('w',encoding='utf-8') as b:
  child=subprocess.Popen(cmd,cwd=d,stdout=a,stderr=b,env=env,creationflags=subprocess.CREATE_NO_WINDOW);start=time.time()
  while child.poll() is None:
   avail=psutil.virtual_memory().available;free=shutil.disk_usage(O).free
   with guard:
    with (O/'resources.jsonl').open('a',encoding='utf-8') as log:log.write(json.dumps({'time':time.time(),'job':d.name,'pid':child.pid,'availableGiB':avail/2**30,'EfreeGiB':free/2**30})+'\n')
   if avail<1*2**30 or free<8*2**30 or time.time()-start>3600:child.kill();child.wait();raise RuntimeError('资源保护触发')
   time.sleep(5)
 assert child.returncode==0,(d,(d/'stderr.log').read_text(encoding='utf-8')[-1500:])
 return sorted(d.glob('output-*/metric.json'))[-1].parent

def export(out,path):
 entries={}
 for line in (out/'code.txt').read_text(encoding='utf-8').splitlines():
  v=line.split('\t')
  if len(v)<5 or len(v[0])!=1:continue
  for code,rank in [(v[1],int(v[2])),(v[3],int(v[4]))]:
   if re.fullmatch('[a-z]{1,4}',code):entries[v[0],code]=min(entries.get((v[0],code),999),rank)
 rows=sorted(entries.items(),key=lambda kv:(len(kv[0][1]),kv[0][1],kv[1],kv[0][0]))
 path.write_text(''.join(f'{c}\t{code}\n' for ((c,code),rank) in rows),encoding='utf-8')

base=read(F/'字音基准.json');new=read(W/'32_多来源字频重建/分音字频_试验.json');by={};oldtot={}
for r in base:by.setdefault(r['字'],[]).append(r);oldtot[r['字']]=oldtot.get(r['字'],0)+r['频率']
boxt={c:int(n) for c,n in (l.split('\t') for l in (W/'30_形码盒子1.0复测/默认字频.txt').read_text().strip().splitlines())};total=sum(r['频率'] for r in base);boxsum=sum(boxt.get(c,0) for c in by)
frequencies={'老表':{(r['字'],r['拼音']):r['频率'] for r in base},'新表':{(r['字'],r['拼音']):r['频率']*total/1e6 for r in new},'盒子表':{}}
for r in new:
 ratio=r['频率']/r['整字频率'] if r['整字频率']>0 else 1/len(by[r['字']])
 frequencies['盒子表'][r['字'],r['拼音']]=boxt.get(r['字'],0)*total/boxsum*ratio
for label,freq in frequencies.items():
 t=sum(v for (c,p),v in freq.items() if c=='谁')
 for key in list(freq):
  if key[0]=='谁':freq[key]=0 if key[1]=='shei' else t/4
 el=yaml.safe_load((F/'elements.yaml').read_text(encoding='utf-8'));chars=[];other=[]
 for e in el:
  key=(e['词'],e.get('拼音'))
  if key in freq:e['频率']=round(freq[key]);chars.append(e)
  else:other.append(e)
 chars.sort(key=lambda e:(-e['频率'],e['词'],e['拼音']));assert len(chars)==8454
 (O/(label+'_elements.yaml')).write_text(yaml.safe_dump(chars+other,allow_unicode=True,sort_keys=False),encoding='utf-8')

cfg=read(W/'27_删利根参数0晋级赛/jobs/g01_projection_01/search/run.json');cfg['optimization']['metaheuristic']['parameters']['steps']=50000;cfg['optimization']['metaheuristic']['update_interval']=2000;cfg['optimization']['metaheuristic']['report_after']=.99
write(O/'共同起点.json',cfg)
write(O/'实验约定.json',{'参考完成方案':'g01_projection_01','种子':seed,'起点':'该方案保存的search/run.json，未取它优化后的布局','说明':'旧程序未记录内部随机流；这次三组在种子版引擎上重新跑，不宣称复现旧结果。','唯一区别':'输入字音频率及其排名；共同规则一致','盒子分音':'按新表自然分音比例拆整字频率；不是盒子原生读音数据','盒子缺失核心字':len(set(by)-set(boxt)),'盒子表外于核心字':len(set(boxt)-set(by)),'缺失处理':'根集字集不变，未覆盖频率0，不补旧频；所有来源缩放到同一旧表总量，之后统一应用谁规则','字集':len(by),'字音项':8454,'步数':50000,'测评':'老表/新表/盒子整字频率交叉测评同一批结果，分档列出；并非多种子显著性检验'})
try:
 write(O/'status.json',{'状态':'重复性短跑验证'})
 semantic=run('encode',cfg,O/'老表_elements.yaml',O/'seeded_encode_check')
 raw=O/'frozen_encode_check';raw.mkdir(exist_ok=True);write(raw/'run.json',cfg)
 with (raw/'stdout.log').open('w',encoding='utf-8') as a,(raw/'stderr.log').open('w',encoding='utf-8') as b:
  subprocess.run([str(F/'chai.exe'),'encode',str(raw/'run.json'),'-e',str(O/'老表_elements.yaml'),'-k',str(F/'distribution.txt'),'-p',str(F/'equivalence.txt')],cwd=raw,stdout=a,stderr=b,check=True,timeout=120)
 original=sorted(raw.glob('output-*/metric.json'))[-1].parent
 assert (semantic/'code.txt').read_bytes()==(original/'code.txt').read_bytes(),'种子版与冻结引擎编码不同'
 assert abs(read(semantic/'metric.json')['score']-read(original/'metric.json')['score'])<1e-7
 small=json.loads(json.dumps(cfg));small['optimization']['metaheuristic']['parameters']['steps']=2000
 a=run('optimize',small,O/'老表_elements.yaml',O/'repeat_a');b=run('optimize',small,O/'老表_elements.yaml',O/'repeat_b')
 assert (a/'code.txt').read_bytes()==(b/'code.txt').read_bytes(),'相同种子输出不一致'
 assert read(a/'metric.json')['score']==read(b/'metric.json')['score']
 # Compare engine encode semantics against the previously frozen executable on identical inputs.
 write(O/'随机重复性核验.json',{'seed':seed,'步数':2000,'同种子同输入码表逐字节一致':True,'分数完全一致':True,'sha256':hashlib.sha256((a/'code.txt').read_bytes()).hexdigest(),'引擎sha256':hashlib.sha256((O/'chai-seeded.exe').read_bytes()).hexdigest()})
 write(O/'status.json',{'状态':'三组五万步运行中','seed':seed})
 def arm(label):
  el=O/(label+'_elements.yaml');d=O/label;d.mkdir(exist_ok=True)
  start=run('encode',cfg,el,d/'起点');out=run('optimize',cfg,el,d/'五万步');final=yaml.safe_load((out/'config.yaml').read_text(encoding='utf-8'));final['generated_mapping_space']=cfg['generated_mapping_space'];v=run('encode',final,el,d/'复核')
  assert (out/'code.txt').read_bytes()==(v/'code.txt').read_bytes()
  assert abs(read(out/'metric.json')['score']-read(v/'metric.json')['score'])<1e-7
  export(out,O/(label+'_五万步单字表.txt'));export(start,O/(label+'_起点单字表.txt'))
  result={'输出目录':str(out),'原生':read(out/'metric.json'),'起点':read(start/'metric.json'),'复核':True};write(d/'result.json',result);print(label+' completed',flush=True);return label,result
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=dict(pool.map(arm,frequencies))
 write(O/'原生结果.json',results)
 subprocess.run(['D:/nodejs/node.exe',str(O/'evaluate.mjs')],cwd=O,check=True,timeout=120)
 write(O/'status.json',{'状态':'完成','seed':seed});print('ALL COMPLETE',flush=True)
except Exception as e:write(O/'status.json',{'状态':'失败','error':str(e)});raise
