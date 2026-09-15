from pathlib import Path
import json,yaml,subprocess,psutil,time,hashlib,traceback,html,shutil
W=Path(__file__).resolve().parent.parent;P=W/'32_多来源字频重建';F=W/'27_删利根参数0晋级赛/frozen';O=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def status(s,**kw):
 write(O/'status.json',{'状态':s,**kw});(O/'进度.html').write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="30"><h1>新字频五万步试验</h1><pre>'+html.escape(json.dumps({'状态':s,**kw},ensure_ascii=False,indent=2))+'</pre>',encoding='utf-8')
def run(mode,cfg,d):
 d.mkdir(exist_ok=True);write(d/'run.json',cfg)
 cmd=[str(F/'chai.exe'),mode,str(d/'run.json'),'-e',str(O/'elements.yaml'),'-k',str(F/'distribution.txt'),'-p',str(F/'equivalence.txt')]
 if mode=='optimize':cmd+=['-t','1']
 assert psutil.virtual_memory().available>4*2**30
 with (d/'stdout.log').open('w',encoding='utf-8') as a,(d/'stderr.log').open('w',encoding='utf-8') as b:
  child=subprocess.Popen(cmd,cwd=d,stdout=a,stderr=b,creationflags=subprocess.CREATE_NO_WINDOW);start=time.time()
  while child.poll() is None:
   avail=psutil.virtual_memory().available;free=shutil.disk_usage(O).free
   with (O/'resources.jsonl').open('a',encoding='utf-8') as log:log.write(json.dumps({'time':time.time(),'pid':child.pid,'availableGiB':avail/2**30,'EfreeGiB':free/2**30})+'\n')
   if avail<1*2**30 or free<8*2**30 or time.time()-start>14400:child.kill();child.wait();raise RuntimeError('资源保护或4小时上限触发')
   status(mode,pid=child.pid,elapsedSeconds=round(time.time()-start),availableGiB=round(avail/2**30,2));time.sleep(10)
 assert child.returncode==0,(d,(d/'stderr.log').read_text(encoding='utf-8')[-2000:])
 return sorted(d.glob('output-*/metric.json'))[-1].parent
try:
 base=read(F/'字音基准.json');new=read(P/'分音字频_试验.json');scale=sum(r['频率'] for r in base)/1e6
 freq={(r['字'],r['拼音']):round(r['优化权重']*scale) for r in new}
 el=yaml.safe_load((F/'elements.yaml').read_text(encoding='utf-8'));chars=[];other=[]
 for e in el:
  k=(e['词'],e.get('拼音'))
  if k in freq:e['频率']=freq[k];chars.append(e)
  else:other.append(e)
 assert len(chars)==8454
 chars.sort(key=lambda e:(-e['频率'],e['词'],e['拼音']));el=chars+other
 (O/'elements.yaml').write_text(yaml.safe_dump(el,allow_unicode=True,sort_keys=False),encoding='utf-8')
 cfg=read(F/'initial.json');cfg['optimization']['metaheuristic']['parameters']['steps']=50000;cfg['optimization']['metaheuristic']['update_interval']=2000;cfg['optimization']['metaheuristic']['report_after']=.99
 write(O/'实验冻结说明.json',{'起点':'旧晋级赛同类projection，1.0投影到删利后133组根集','步数':50000,'并行':1,'输入频率':'新分音估计权重缩放并整数化；谁独立规则已应用','scale':scale,'字音项':len(chars),'保留简词位':len(other),'未进行':'正式晋级赛；修改27输入；D盘写入','原生随机流':'未固定，单次探索结果不代表统计显著','sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [F/'initial.json',F/'elements.yaml',P/'分音字频_试验.json',O/'elements.yaml']}})
 startout=run('encode',cfg,O/'起点');out=run('optimize',cfg,O/'五万步')
 final=yaml.safe_load((out/'config.yaml').read_text(encoding='utf-8'));final['generated_mapping_space']=cfg['generated_mapping_space'];ver=run('encode',final,O/'复核')
 assert (out/'code.txt').read_bytes()==(ver/'code.txt').read_bytes()
 assert abs(read(out/'metric.json')['score']-read(ver/'metric.json')['score'])<1e-7
 def export(out,name):
  entries={}
  for line in (out/'code.txt').read_text(encoding='utf-8').splitlines():
   v=line.split('\t')
   if len(v)<5 or len(v[0])!=1:continue
   for code,rank in [(v[1],int(v[2])),(v[3],int(v[4]))]:
    if re.fullmatch('[a-z]{1,4}',code):entries[v[0],code]=min(entries.get((v[0],code),999),rank)
  rows=sorted(entries.items(),key=lambda kv:(len(kv[0][1]),kv[0][1],kv[1],kv[0][0]))
  path=O/name;path.write_text(''.join(f'{c}\t{code}\n' for ((c,code),rank) in rows),encoding='utf-8');return str(path)
 import re
 codes={'起点':export(startout,'起点_普通单字表.txt'),'五万步':export(out,'五万步_普通单字表.txt'),'夜莺1.0':str(W.parents[1]/'releases/v1.0/01_正式码表/夜莺码v1.0单字版.txt')}
 write(O/'测评码表路径.json',codes);write(O/'原生结果.json',{'起点':read(startout/'metric.json'),'五万步':read(out/'metric.json'),'原生复核通过':True})
 subprocess.run(['D:/nodejs/node.exe',str(O/'evaluate.mjs')],cwd=O,check=True,timeout=120)
 status('完成',report=str(O/'双字频当量对照.html'))
except Exception as exc:
 status('失败',error=str(exc));raise
