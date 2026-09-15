from pathlib import Path
P=Path(__file__).resolve().parent
ns={'__file__':str(P/'run.py'),'__name__':'parameter_validation_library'}
exec((P/'run.py').read_text(encoding='utf-8'),ns)
globals().update({k:v for k,v in ns.items() if not k.startswith('__')})

def profile_hash(c):return hashlib.sha256(json.dumps(c['optimization'],sort_keys=True).encode()).hexdigest()
def run_validation():
 write(P/'parameter_status.json',{'status':'waiting_for_rotation','pid':os.getpid()})
 while True:
  s=read(P/'rotation_status.json')
  if s['status']=='failed':raise RuntimeError('轮换阶段失败，先恢复轮换')
  if s['status']=='complete':break
  time.sleep(20)
 if (P/'parameter_profiles.json').exists():profiles=read(P/'parameter_profiles.json')
 else:
  profiles=[];seen=set()
  # Favor profiles supported by replicated original-start runs; add a discovery profile from rotation.
  ranking=read(P/'阶段排名.json')['3']
  for r in [x for x in ranking if x['eligible']][:2]:
   cfg=config(r['recipe'],'A');h=profile_hash(cfg)
   if h not in seen:profiles.append({'source':'第三阶段重复验证','config':cfg,'sha':h});seen.add(h)
  ds=[read(f) for f in (P/'jobs').glob('rotate*/round2.json')]
  ds=[d for d in ds if next(t for t in d['native']['characters_full']['tiers'] if t['top']==300)['effective_duplication']==0]
  for d in sorted(ds,key=lambda d:-d['score']['total']):
   if len(profiles)>=3:break
   cfg=read(P/'jobs'/d['card']['id']/'final_config.json');h=profile_hash(cfg)
   if h not in seen:profiles.append({'source':'轮换探索 '+d['card']['id'],'config':cfg,'sha':h});seen.add(h)
  control=read(P.parent/'23_重码保护范围试跑/configs/A_top6000.json')
  profiles.append({'source':'固定对照：手感1.25、前6000保护','config':control,'sha':profile_hash(control)})
  write(P/'parameter_profiles.json',profiles)
 cards=read(P/'cards.json');batch=[];initial=read(F/'initial.json')['form']['mapping'];groups=sorted(k for k in initial if k.startswith('G'))
 for pi,pr in enumerate(profiles):
  for kind,frac in [('projection',0),('small',.15),('large',.6),('random',1)]:
   for rep in range(2):
    id=f'parameter_{pi}_{kind}_{rep}';cfg=copy.deepcopy(pr['config']);cfg['form']['mapping']=copy.deepcopy(initial)
    seed=202609130000+100*['projection','small','large','random'].index(kind)+rep;rng=random.Random(seed)
    for k in rng.sample(groups,round(len(groups)*frac)):
     cfg['form']['mapping'][k]=rng.choice('abcdefghijklmnopqrstuvwxyz')
    cfg['optimization']['metaheuristic']['parameters']['steps']=50000
    path=P/'configs'/(id+'.json');c={'id':id,'stage':'参数集独立起点验证','recipe':{'profile':pi,'source':pr['source'],'start':kind,'repeat':rep},'tag':'A','steps':50000,'original_config':str(path),'label':id,'profile':pi,'start_kind':kind,'seed':seed}
    if not any(x['id']==id for x in cards):write(path,cfg);cards.append(c)
    batch.append(c)
 write(P/'cards.json',cards);write(P/'parameter_status.json',{'status':'running','total':len(batch),'pid':os.getpid()})
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
  for f in concurrent.futures.as_completed([executor.submit(run_one,c) for c in batch]):
   f.result();write(P/'parameter_status.json',{'status':'running','completed':sum((P/'jobs'/c['id']/'round2.json').exists() for c in batch),'total':len(batch),'pid':os.getpid()})
 summaries=[];raw={}
 for pi,pr in enumerate(profiles):
  ds=[get_result(c) for c in batch if c['profile']==pi];flat=[flatten(d) for d in ds];scores=[d['score']['total'] for d in ds]
  passes=[next(t for t in d['native']['characters_full']['tiers'] if t['top']==300)['effective_duplication']==0 for d in ds]
  metrics={k:{'mean':statistics.mean(v[k] for v in flat),'min':min(v[k] for v in flat),'max':max(v[k] for v in flat),'sd':statistics.pstdev(v[k] for v in flat)} for k in flat[0]}
  bystart={k:[d['score']['total'] for d in ds if d['card']['start_kind']==k] for k in ['projection','small','large','random']}
  summaries.append({'参数集':pi,'来源':pr['source'],'次数':len(ds),'平均综合分':statistics.mean(scores),'最差综合分':min(scores),'标准差':statistics.pstdev(scores),'前300无有效重码通过率':sum(passes)/len(passes)})
  raw[str(pi)]={'参数SHA256':pr['sha'],'指标统计':metrics,'各起点分数':bystart,'门槛通过':passes,'样本':[d['card']['id'] for d in ds]}
  write(P/'参数集交付'/f'profile_{pi}.json',{'optimization':pr['config']['optimization'],'source':pr['source'],'note':'只含搜索参数；配合本批冻结根集、元素表、编码规则和简码约定使用。'})
 write(P/'参数集稳定性.json',{'概览':summaries,'完整统计':raw,'注意':'共享起点但原生随机流未固定；同一开发语料反复评价，不宣称独立泛化或显著性。不得按单次最高分定参数。失败门槛样本保留在平均与统计中。'})
 ks=list(summaries[0]);table='<table><tr>'+''.join('<th>'+k+'</th>' for k in ks)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in ks)+'</tr>' for r in summaries)+'</table>'
 (P/'参数集验证.html').write_text('<!doctype html><meta charset="utf-8"><title>退火参数集稳定性验证</title><style>body{font:16px system-ui;margin:30px}td,th{border:1px solid #ccc;padding:10px}table{border-collapse:collapse}</style><h1>选参数集，不选幸运码表</h1><p>每组四种独立起点，各运行两次，50,000步；共用相同起点布局，沿用固定计分。原生随机流未固定。所有失败门槛样本也计入统计。完整分指标均值、波动与起点差异见参数集稳定性.json。</p>'+table,encoding='utf-8')
 write(P/'parameter_status.json',{'status':'complete','completed':len(batch),'profiles':len(profiles)})

if __name__=='__main__':
 try:run_validation()
 except Exception:
  (P/'parameter_error.txt').write_text(traceback.format_exc(),encoding='utf-8');write(P/'parameter_status.json',{'status':'failed'});raise
