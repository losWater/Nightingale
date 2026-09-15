from common import *
import subprocess,psutil

def optimize(card,where):
 done=where/'optimized.json'
 if done.exists():
  old=read(done);assert old['primary_guard_pass'];return old
 original=read(F/'initial.json');cfg=copy.deepcopy(original);rng=random.Random(card['seed'])
 keys=sorted(k for k in cfg['form']['mapping'] if k.startswith('G'))
 n={'projection':0,'small':SET['small_groups'],'large':SET['large_groups'],'random':len(keys)}[card['kind']]
 for k in rng.sample(keys,n):
  allowed=[x['value'] for x in cfg['generated_mapping_space'][k]]
  if card['kind']!='random':allowed=[x for x in allowed if x!=cfg['form']['mapping'][k]]
  cfg['form']['mapping'][k]=rng.choice(allowed)
 cfg['optimization']['metaheuristic']['parameters']['steps']=SET['steps']
 write(where/'initial.json',cfg)
 initial=copy.deepcopy(cfg)
 manifest=read(F/'主读音保护清单.json')['字表']
 def failures(out):
  rows=[l.split('\t') for l in (out/'code.txt').read_text(encoding='utf8').splitlines()];bad=[]
  for m in manifest:
   r=rows[m['输入索引']];assert r[0]==m['字']
   if not ((r[1] and int(r[2])==0) or (r[3] and int(r[4])==0)):bad.append(m['字'])
  return bad
 def execute(mode,config,folder,repair=False,seed=None):
  folder.mkdir(parents=True,exist_ok=True);write(folder/'run.json',config)
  env=dict(os.environ,NIGHTINGALE_TRIAL_SEED=str(card['seed'] if seed is None else seed),NIGHTINGALE_PRIMARY_GUARD=str(F/'guard_indices.json'),NIGHTINGALE_TARGET_DIR=str(F),NIGHTINGALE_TARGET_WEIGHT='200')
  env.pop('NIGHTINGALE_REPAIR',None)
  if repair:env['NIGHTINGALE_REPAIR']='1'
  env['TEMP']=str(ROOT/'tmp');env['TMP']=env['TEMP'];(ROOT/'tmp').mkdir(exist_ok=True)
  cmd=[str(F/'chai.exe'),mode,str(folder/'run.json'),'-e',str(F/'elements.yaml'),'-k',str(F/'distribution.txt'),'-p',str(F/'equivalence.txt')]
  if mode=='optimize':cmd+=['-t','1']
  with (folder/'stdout.log').open('w',encoding='utf8') as o,(folder/'stderr.log').open('w',encoding='utf8') as e:
   proc=subprocess.Popen(cmd,cwd=folder,stdout=o,stderr=e,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
   try:psutil.Process(proc.pid).nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
   except psutil.Error:pass
   try:rc=proc.wait(timeout=SET['max_task_hours']*3600)
   except subprocess.TimeoutExpired:proc.kill();proc.wait();raise
  assert rc==0,(mode,folder,(folder/'stderr.log').read_text(encoding='utf8')[-1500:])
  out=max(folder.glob('output-*/metric.json'),key=lambda p:p.stat().st_mtime).parent
  return out,read(out/'metric.json')
 start,_=execute('encode',cfg,where/'initial_check');bad=failures(start)
 repair_record={'initial_missing':bad,'attempts':[],'kind':card['kind'],'initial_distance':sum(cfg['form']['mapping'][k]!=original['form']['mapping'][k] for k in keys)}
 if bad:
  for attempt in range(SET['repair_attempts']):
   repair=copy.deepcopy(initial);repair['optimization']['metaheuristic']['parameters']={'t_max':1,'t_min':.01,'steps':SET['repair_steps']}
   repair['optimization']['objective']['regularization_strength']=1
   for k,vs in repair['generated_mapping_space'].items():
    for v in vs:v['score']=0.0 if v['value']==initial['form']['mapping'][k] else 10.0
   folder=where/f'repair_{attempt+1}'
   out,rm=execute('optimize',repair,folder,True,card['seed']+attempt*1000000)
   log=(folder/'stderr.log').read_text(encoding='utf8');delta=float(re.search(r'TRIAL_CACHE_DELTA ([^\s]+)',log)[1]);assert delta<1e-6
   remaining=failures(out);repair_record['attempts'].append({'attempt':attempt+1,'remaining':remaining,'steps':int(re.search(r'STAGE_REPAIR true EXECUTED (\d+)',log)[1]),'cache_delta':delta});write(where/'repair.json',repair_record)
   if remaining:continue
   cfg=yload(out/'config.yaml');cfg['generated_mapping_space']=initial['generated_mapping_space'];cfg['optimization']=copy.deepcopy(initial['optimization'])
   vo,vm=execute('encode',cfg,where/'repair_verify');assert (out/'code.txt').read_bytes()==(vo/'code.txt').read_bytes()
   moved=sum(cfg['form']['mapping'][k]!=initial['form']['mapping'][k] for k in keys)
   assert abs(rm['score']-10*moved-vm['score'])<1e-6
   repair_record['moved_groups']=moved;break
  else:raise RuntimeError('起点修复预算耗尽，不进入硬约束搜索：'+str(remaining))
 repair_record['feasible_distance']=sum(cfg['form']['mapping'][k]!=original['form']['mapping'][k] for k in keys)
 write(where/'repair.json',repair_record);write(where/'feasible_start.json',cfg)
 assert cfg['optimization']==initial['optimization'] and cfg['generated_mapping_space']==initial['generated_mapping_space']
 assert all(cfg['form']['mapping']['P_'+k]==k for k in 'abcdefghijklmnopqrstuvwxyz')
 out,met=execute('optimize',cfg,where/'search');assert not failures(out)
 log=(where/'search/stderr.log').read_text(encoding='utf8');assert f'STAGE_REPAIR false EXECUTED {SET["steps"]}' in log
 delta=float(re.search(r'TRIAL_CACHE_DELTA ([^\s]+)',log)[1]);assert delta<1e-7
 final=yload(out/'config.yaml');final['generated_mapping_space']=cfg['generated_mapping_space']
 vo,vm=execute('encode',final,where/'verify');assert abs(vm['score']-met['score'])<1e-7
 assert (out/'code.txt').read_bytes()==(vo/'code.txt').read_bytes() and not failures(vo)
 ns={'elements':{'elements.yaml':yload(F/'elements.yaml')},'Counter':Counter,'defaultdict':defaultdict,'json':json}
 source=(F/'validation_base.py').read_text(encoding='utf8');exec(source[source.index('def validate('):source.index('starts=[]')],ns)
 efficiency=ns['validate'](out,'elements.yaml');ns['validate'](vo,'elements.yaml')
 write(where/'final_config.json',final);layout={k:final['form']['mapping'][k] for k in keys}
 result={'code':str(out/'code.txt'),'native':met['metric'],'native_score':met['score'],'efficiency':efficiency,'layout':layout,'layout_hash':hashlib.sha256(json.dumps(layout,sort_keys=True).encode()).hexdigest(),'cache_delta':delta,'primary_guard_pass':True,'code_sha256':sha(out/'code.txt')}
 write(done,result);return result
