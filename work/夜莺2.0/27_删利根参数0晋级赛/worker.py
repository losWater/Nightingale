from common import *
import subprocess,traceback,psutil,argparse

def optimize(card,where):
 done=where/'optimized.json'
 if done.exists():return read(done)
 cfg=read(F/'initial.json');rng=random.Random(card['seed']);mapping=cfg['form']['mapping'];groups=sorted(k for k in mapping if k.startswith('G'))
 kind=card['kind'];fraction={'projection':0,'small':SET['small_fraction'],'large':SET['large_fraction'],'random':1}[kind]
 for k in rng.sample(groups,round(len(groups)*fraction)):
  mapping[k]=rng.choice([c for c in 'abcdefghijklmnopqrstuvwxyz' if c!=mapping[k]]) if kind!='random' else rng.choice('abcdefghijklmnopqrstuvwxyz')
 assert cfg['optimization']==read(F/'initial.json')['optimization'], '参数0不得二次加权'
 cfg['optimization']['metaheuristic']['parameters']['steps']=SET['steps']
 cfg['optimization']['metaheuristic']['update_interval']=2000;cfg['optimization']['metaheuristic']['report_after']=.99
 run=where/'search';run.mkdir(parents=True,exist_ok=True);write(run/'run.json',cfg)
 def execute(mode,config,folder):
  folder.mkdir(parents=True,exist_ok=True);write(folder/'run.json',config)
  cmd=[str(F/'chai.exe'),mode,str(folder/'run.json'),'-e',str(F/'elements.yaml'),'-k',str(F/'distribution.txt'),'-p',str(F/'equivalence.txt')]
  if mode=='optimize':cmd+=['-t','1']
  with (folder/'stdout.log').open('w',encoding='utf-8') as o,(folder/'stderr.log').open('w',encoding='utf-8') as e:
   child=subprocess.Popen(cmd,cwd=folder,stdout=o,stderr=e,creationflags=subprocess.CREATE_NO_WINDOW)
   try:psutil.Process(child.pid).nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
   except psutil.Error:pass
   try:rc=child.wait(timeout=SET['max_task_hours']*3600)
   except subprocess.TimeoutExpired:
    child.kill();child.wait();raise
  assert rc==0,(mode,rc)
  out=sorted(folder.glob('output-*/metric.json'))[-1].parent;return out,read(out/'metric.json')
 out,met=execute('optimize',cfg,run)
 log=(run/'stderr.log').read_text(encoding='utf-8');delta=float(re.search(r'TRIAL_CACHE_DELTA ([^\s]+)',log)[1]);assert delta<1e-7
 final=yload(out/'config.yaml');final['generated_mapping_space']=cfg['generated_mapping_space']
 assert all(final['form']['mapping']['P_'+k]==k for k in 'abcdefghijklmnopqrstuvwxyz')
 assert all(final['form']['mapping'][k] in 'abcdefghijklmnopqrstuvwxyz' for k in groups)
 vo,vm=execute('encode',final,where/'verify');assert abs(vm['score']-met['score'])<1e-7
 ns={'elements':{'elements.yaml':yload(F/'elements.yaml')},'Counter':Counter,'defaultdict':defaultdict,'json':json}
 source=(F/'validation_base.py').read_text(encoding='utf-8');exec(source[source.index('def validate('):source.index('starts=[]')],ns)
 efficiency=ns['validate'](out,'elements.yaml');ns['validate'](vo,'elements.yaml')
 assert (out/'code.txt').read_bytes()==(vo/'code.txt').read_bytes()
 write(where/'final_config.json',final)
 layout={k:final['form']['mapping'][k] for k in groups}
 result={'code':str(out/'code.txt'),'native':met['metric'],'native_score':met['score'],'efficiency':efficiency,'layout':layout,'layout_hash':hashlib.sha256(json.dumps(layout,sort_keys=True).encode()).hexdigest(),'cache_delta':delta}
 write(done,result);return result

def work(card,roundno,details=False):
 where=ROOT/'jobs'/card['id'];where.mkdir(parents=True,exist_ok=True)
 if roundno==1:
  optimized=optimize(card,where);theory=theory_data(optimized['native'],optimized['code']);write(where/'theory.json',theory)
 else:optimized=read(where/'optimized.json');theory=read(where/'theory.json')
 ns=bench_module(roundno,ROOT/f'round{roundno}',details);bench=ns['run'](Path(optimized['code']),card['id']);score=combine(theory,bench)
 result={'id':card['id'],'group':card['group'],'kind':card['kind'],'round':roundno,'score':score,'layout_hash':optimized['layout_hash'],'theory':theory,'benchmark_path':str(ROOT/f'round{roundno}'/'results'/card['id']/'结果.json')}
 write(where/f'round{roundno}.json',result)
 return result
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('id');ap.add_argument('--round',type=int,default=1);ap.add_argument('--details',action='store_true');args=ap.parse_args()
 try:
  psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
  card=next(c for c in read(ROOT/'cards.json') if c['id']==args.id);work(card,args.round,args.details)
 except Exception:
  (ROOT/'jobs'/args.id).mkdir(parents=True,exist_ok=True)
  (ROOT/'jobs'/args.id/f'error_round{args.round}.txt').write_text(traceback.format_exc(),encoding='utf-8');raise
