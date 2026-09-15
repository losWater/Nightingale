from pathlib import Path
import json,yaml,subprocess,psutil,time,hashlib,html,os,re,concurrent.futures,threading,shutil,ast
O=Path(__file__).resolve().parent;W=O.parent;F=W/'27_删利根参数0晋级赛/frozen';seed=202609121702;guard=threading.Lock()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
# Reuse the tested process/resource guard and plain-table exporter, without executing prior experiments.
tree=ast.parse((W/'35_同种子三字频对照/controller.py').read_text(encoding='utf-8-sig'));source=ast.unparse(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('run','export')],type_ignores=[]));source=source.replace("NIGHTINGALE_TRIAL_SEED=str(seed)", "NIGHTINGALE_TRIAL_SEED=str(read(d.parent/'job.json')['seed']), NIGHTINGALE_PRIMARY_GUARD=str(O/'guard_indices.json'), NIGHTINGALE_TARGET_DIR=str(d.parent), NIGHTINGALE_TARGET_WEIGHT=str(read(d.parent/'job.json')['weight'])");exec(source)
def check_gate(out):
 lines=[l.split('\t') for l in (out/'code.txt').read_text(encoding='utf8').splitlines()]
 for m in read(O/'主读音保护清单.json')['字表']:
  r=lines[m['输入索引']];assert r[0]==m['字']
  assert (r[1] and int(r[2])==0) or (r[3] and int(r[4])==0),(m,r)
try:
 labels=[j['id'] for j in read(O/'jobs.json')];write(O/'status.json',{'状态':'运行中','方案':labels,'seeds':[202609121703,202609121704],'steps':50000})
 def arm(label):
  d=O/label;cfg=read(d/'initial.json');el=d/'elements.yaml'
  start=run('encode',cfg,el,d/'起点');check_gate(start);out=run('optimize',cfg,el,d/'五万步');final=yaml.load((out/'config.yaml').read_text(encoding='utf-8'),Loader=yaml.CSafeLoader);final['generated_mapping_space']=cfg['generated_mapping_space'];v=run('encode',final,el,d/'复核')
  assert (out/'code.txt').read_bytes()==(v/'code.txt').read_bytes()
  assert abs(read(out/'metric.json')['score']-read(v/'metric.json')['score'])<1e-7
  assert re.search(r'已执行 50000 步',(d/'五万步/stdout.log').read_text(encoding='utf-8'))
  delta=float(re.search(r'TRIAL_CACHE_DELTA ([^\s]+)',(d/'五万步/stderr.log').read_text(encoding='utf-8'))[1]);assert abs(delta)<1e-7
  check_gate(out)
  export(out,O/(label+'_五万步单字表.txt'));export(start,O/(label+'_起点单字表.txt'))
  result={'输出目录':str(out),'原生':read(out/'metric.json'),'起点':read(start/'metric.json'),'复核':True,'缓存差异':delta};write(d/'result.json',result);print(label+' completed',flush=True);return label,result
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=dict(pool.map(arm,labels))
 write(O/'原生结果.json',results)
 subprocess.run(['D:/nodejs/node.exe',str(O/'evaluate.mjs')],cwd=O,check=True,timeout=120)
 subprocess.run([os.sys.executable,str(O/'report.py')],cwd=O,check=True,timeout=120)
 write(O/'status.json',{'状态':'完成','seeds':[202609121703,202609121704]});print('ALL COMPLETE',flush=True)
except Exception as e:write(O/'status.json',{'状态':'失败','error':str(e)});raise
