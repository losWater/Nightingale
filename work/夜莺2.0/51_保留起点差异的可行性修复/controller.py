from pathlib import Path
import json,yaml,subprocess,psutil,time,hashlib,html,os,re,concurrent.futures,threading,shutil,ast
O=Path(__file__).resolve().parent;W=O.parent;F=W/'27_删利根参数0晋级赛/frozen';guard=threading.Lock();seed=0
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
tree=ast.parse((W/'35_同种子三字频对照/controller.py').read_text(encoding='utf8'))
source=ast.unparse(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('run','export')],type_ignores=[]))
source=source.replace('NIGHTINGALE_TRIAL_SEED=str(seed)',"NIGHTINGALE_TRIAL_SEED=str(read(d.parent/'job.json')['seed']), NIGHTINGALE_PRIMARY_GUARD=str(O/'guard_indices.json'), NIGHTINGALE_TARGET_DIR=str(d.parent), NIGHTINGALE_TARGET_WEIGHT='200'")
source=source.replace('assert psutil.virtual_memory()',"env.pop('NIGHTINGALE_REPAIR',None)\n    if read(d.parent/'job.json')['repair']: env['NIGHTINGALE_REPAIR']='1'\n    assert psutil.virtual_memory()")
exec(source)
manifest=read(O/'主读音保护清单.json')['字表'];reference=read(O/'参考布局.json')
def failure(out):
 lines=[l.split('\t') for l in (out/'code.txt').read_text(encoding='utf8').splitlines()];bad=[]
 for m in manifest:
  r=lines[m['输入索引']];assert r[0]==m['字']
  if not ((r[1] and int(r[2])==0) or (r[3] and int(r[4])==0)):bad.append({'字':m['字'],'音':m['拼音'],'全码':r[1],'简码':r[3]})
 return bad
def mapping(out):return yaml.load((out/'config.yaml').read_text(encoding='utf8'),Loader=yaml.CSafeLoader)
def distance(a,b):return sum(a['form']['mapping'][k]!=b['form']['mapping'][k] for k in a['form']['mapping'] if k.startswith('G'))
def arm(j):
 d=O/j['id'];initial=read(d/'initial.json');el=d/'elements.yaml';start=run('encode',initial,el,d/'起点');bad=failure(start)
 result={'id':j['id'],'类型':j['type'],'种子':j['seed'],'初始主音缺口':len(bad),'初始不达标':bad,'初始偏离基线根组':distance(initial,reference),'修复步数':0}
 cfg=initial
 if bad:
  repair=json.loads(json.dumps(initial));repair['optimization']['metaheuristic']['parameters']={'t_max':1,'t_min':0.01,'steps':50000}
  repair['optimization']['objective']['regularization_strength']=1.0
  for k,vs in repair['generated_mapping_space'].items():
   for v in vs:v['score']=0.0 if v['value']==initial['form']['mapping'][k] else 10.0
  j['repair']=True;write(d/'job.json',j)
  out=run('optimize',repair,el,d/'修复')
  log=(d/'修复/stderr.log').read_text(encoding='utf8');result['修复步数']=int(re.search(r'STAGE_REPAIR true EXECUTED (\d+)',log)[1]);result['修复缓存差']=float(re.search(r'TRIAL_CACHE_DELTA ([^\s]+)',log)[1])
  assert result['修复缓存差']<1e-6
  cfg=mapping(out);cfg['generated_mapping_space']=initial['generated_mapping_space'];cfg['optimization']=json.loads(json.dumps(initial['optimization']))
  j['repair']=False;write(d/'job.json',j)
  result['修复后不达标']=failure(out)
  if result['修复后不达标']:
   result['状态']='修复未完成，禁止进入硬约束退火';result['剩余缺口']=len(result['修复后不达标']);write(d/'result.json',result);print(json.dumps(result,ensure_ascii=False),flush=True);return j['id'],result
  verify=run('encode',cfg,el,d/'修复重编码')
  assert (out/'code.txt').read_bytes()==(verify/'code.txt').read_bytes()
  assert abs(read(out/'metric.json')['score']-10.0*distance(cfg,initial)-read(verify/'metric.json')['score'])<1e-6
 result['可行起点偏离基线根组']=distance(cfg,reference);result['修复改变初始根组']=distance(cfg,initial)
 write(d/'可行起点.json',cfg)
 cfg['optimization']['metaheuristic']=initial['optimization']['metaheuristic']
 out=run('optimize',cfg,el,d/'硬约束5000步');assert not failure(out)
 final=mapping(out);final['generated_mapping_space']=initial['generated_mapping_space']
 verify=run('encode',final,el,d/'终点重编码');assert (out/'code.txt').read_bytes()==(verify/'code.txt').read_bytes()
 assert abs(read(out/'metric.json')['score']-read(verify/'metric.json')['score'])<1e-7
 log=(d/'硬约束5000步/stderr.log').read_text(encoding='utf8');assert 'STAGE_REPAIR false EXECUTED 5000' in log
 delta=float(re.search(r'TRIAL_CACHE_DELTA ([^\s]+)',log)[1]);assert delta<1e-7
 result.update({'状态':'通过','硬约束步数':5000,'正式缓存差':delta,'终点偏离基线根组':distance(final,reference),'终点缺口':0,'原生输出':str(out),'原生':read(out/'metric.json'),'码表指纹':hashlib.sha256((out/'code.txt').read_bytes()).hexdigest()})
 export(out,d/'普通单字表.txt');write(d/'result.json',result);print(j['id']+' PASS',flush=True);return j['id'],result
if __name__=='__main__':
 try:
  write(O/'status.json',{'状态':'起点验证运行中','正式大跑':False})
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=dict(pool.map(arm,read(O/'jobs.json')))
  write(O/'结果.json',results)
  subprocess.run([os.sys.executable,str(O/'report.py')],check=True,cwd=O)
  write(O/'status.json',{'状态':'验证完成','通过':sum(r['状态']=='通过' for r in results.values()),'总数':len(results),'正式大跑':False})
 except Exception as e:write(O/'status.json',{'状态':'失败','错误':str(e)});raise
