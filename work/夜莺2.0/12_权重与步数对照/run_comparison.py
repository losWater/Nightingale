from pathlib import Path
import json,copy,yaml,concurrent.futures,re,time,hashlib
O=Path(__file__).resolve().parent;A=O.parent/'11_多起点试跑'
source=(A/'run_trial.py').read_text(encoding='utf-8').split('starts=[]')[0]
source='\n'.join('configs={}' if line.startswith('configs=') else line for line in source.splitlines())
ns={'__file__':str(A/'run_trial.py')};exec(source,ns)
execute=ns['execute'];validate=ns['validate']
base=json.loads((A/'02_perturbed/short_run/run.json').read_text(encoding='utf-8'))['optimization']['objective']
cards=[]
for start in ['02_perturbed','05_random']:
 original=json.loads((A/start/'short_run/run.json').read_text(encoding='utf-8'))
 for mode in ['baseline','three_plus','word_plus']:
  cfg=copy.deepcopy(original)
  if mode=='three_plus':
   for t in cfg['optimization']['objective']['characters_short']['tiers']:
    for level in t.get('levels',[]):
     if level['length']==3:level['frequency']*=1.25
  if mode=='word_plus':cfg['optimization']['objective']['character_word_collision']['weight']*=1.5
  cfg['optimization']['metaheuristic']['parameters']['steps']=20000
  cfg['optimization']['metaheuristic']['update_interval']=2000
  cfg['optimization']['metaheuristic']['report_after']=.99
  cards.append({'id':start+'_'+mode,'start':start,'mode':mode,'elements':'elements.yaml','cfg':cfg})
paired=copy.deepcopy(cards[0]);paired['id']='02_perturbed_baseline_ji_ju';paired['elements']='elements_ji_ju.yaml';paired['mode']='baseline_ji_ju';cards.append(paired)
manifest={'status':'running','steps_per_run':20000,'conditions':'2 shared initial layouts x 3 weight settings, plus one identical-layout alternate split; RNG native unseeded, not common random stream','weights':'baseline; three-code rewards x1.25; word collision weight x1.5','results':[],'cards':[{k:v for k,v in c.items() if k!='cfg'} for c in cards]}
(O/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
def run(c):
 d=O/c['id'];t=time.time();out,met=execute(c['cfg'],d/'search',c['elements'],'optimize');v=validate(out,c['elements'])
 log=(d/'search/stderr.log').read_text(encoding='utf-8');delta=float(re.search(r'TRIAL_CACHE_DELTA ([^\s]+)',log)[1]);assert delta<1e-7,(c['id'],delta)
 cfg=yaml.safe_load((out/'config.yaml').read_text(encoding='utf-8'));cfg['generated_mapping_space']=c['cfg']['generated_mapping_space']
 vo,vm=execute(cfg,d/'verify',c['elements']);validate(vo,c['elements']);assert abs(vm['score']-met['score'])<1e-7
 assert all(cfg['form']['mapping']['P_'+k]==k for k in 'abcdefghijklmnopqrstuvwxyz')
 common=copy.deepcopy(cfg);common['optimization']['objective']=copy.deepcopy(base)
 co,cm=execute(common,d/'common_score',c['elements'])
 result={'id':c['id'],'start':c['start'],'mode':c['mode'],'elements':c['elements'],'score_own':met['score'],'score_common':cm['score'],'efficiency':v,'metrics':met['metric'],'output':str(out),'seconds':time.time()-t,'cache_delta':delta,'acceptance':re.search(r'TRIAL_ACCEPT .*',log)[0]}
 (d/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print('DONE',c['id'],cm['score'],v['三码及以内首选项数'],flush=True);return result
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 futures=[pool.submit(run,c) for c in cards]
 for f in concurrent.futures.as_completed(futures):
  manifest['results'].append(f.result());(O/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
manifest['status']='complete';(O/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('ALL_COMPLETE',flush=True)
