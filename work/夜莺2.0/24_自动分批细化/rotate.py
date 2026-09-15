from pathlib import Path
P=Path(__file__).resolve().parent
ns={'__file__':str(P/'run.py'),'__name__':'rotation_library'}
exec((P/'run.py').read_text(encoding='utf-8'),ns)
globals().update({k:v for k,v in ns.items() if not k.startswith('__')})

def vector(d):
 b=d['benchmark']['实战'];t=d['theory']['分段']
 return [-d['score']['total'],b['纯单字']['字均当量'],b['无简词字词']['字均当量'],b['无简词字词']['字词增量受影响率'],b['纯单字']['字字选重率_单字上屏'],-sum(x['≤三码首选'] for x in t[:5])]
def frontier(ds):
 return [d for d in ds if not any(all(a<=b for a,b in zip(vector(o),vector(d))) and any(a<b for a,b in zip(vector(o),vector(d))) for o in ds)]
def main_rotation():
 while True:
  s=read(P/'status.json')
  if s['status']=='failed':raise RuntimeError('基础阶段失败，先修复基础阶段再继续')
  if s['status']=='complete':break
  time.sleep(20)
 pool=[read(f) for f in (P/'jobs').glob('*/round2.json')]
 pool=[d for d in pool if next(t for t in d['native']['characters_full']['tiers'] if t['top']==300)['effective_duplication']==0]
 assert pool
 history=[]
 for cycle in [1,2]:
  pf=frontier(pool)
  leaders=[]
  for key in [lambda d:-d['score']['total'],lambda d:d['benchmark']['实战']['纯单字']['字均当量'],lambda d:d['benchmark']['实战']['无简词字词']['字词增量受影响率']]:
   d=min(pf,key=key)
   if d['card']['id'] not in [x['card']['id'] for x in leaders]:leaders.append(d)
  cards=read(P/'cards.json');batch=[]
  for i,parent in enumerate(leaders):
   for direction in ['hand','word','three','heat']:
    id=f'rotate{cycle}_{i}_{direction}';cfg=read(P/'jobs'/parent['card']['id']/'final_config.json');o=cfg['optimization']['objective']
    if direction=='hand':
     o['characters_short']['pair_equivalence']=o['characters_short'].get('pair_equivalence',0)+.5
     for t in o['characters_short']['tiers']:
      if 'weighted_fingering'in t:t['weighted_fingering']=[x*1.1 for x in t['weighted_fingering']]
    elif direction=='word':o['character_word_collision']['weight']*=1.25
    elif direction=='three':
     for t in o['characters_short']['tiers']:
      for v in t.get('levels',[]):
       if v['length']==3:v['frequency']*=1.1
    else:o['characters_short']['key_distribution']=o['characters_short'].get('key_distribution',0)+.5
    path=P/'configs'/(id+'.json');write(path,cfg)
    c={'id':id,'stage':f'轮换{cycle}','recipe':{'parent':parent['card']['id'],'focus':direction},'tag':parent['card']['tag'],'steps':50000,'original_config':str(path),'label':id,'parent':parent['card']['id']}
    if not any(x['id']==id for x in cards):cards.append(c)
    batch.append(c)
  write(P/'cards.json',cards);write(P/'rotation_status.json',{'status':'running','cycle':cycle,'planned':len(batch)})
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
   for f in concurrent.futures.as_completed([executor.submit(run_one,c) for c in batch]):f.result();report(cards)
  for c in batch:
   d=get_result(c);parent=next(x for x in pool if x['card']['id']==c['parent'])
   a=flatten(parent);b=flatten(d)
   history.append({'id':c['id'],'parent':c['parent'],'focus':c['recipe']['focus'],'与直接起点的变化':{k:b[k]-v for k,v in a.items() if k in b},'前300过关':next(t for t in d['native']['characters_full']['tiers'] if t['top']==300)['effective_duplication']==0})
   if history[-1]['前300过关']:pool.append(d)
  write(P/'轮换逐次得失.json',history)
  write(P/'轮换非支配方案.json',[{'id':d['card']['id'],'综合分':d['score']['total'],'指标向量':vector(d)} for d in frontier(pool)])
 write(P/'rotation_status.json',{'status':'complete','cycles':2,'new_runs':len(history)})
 report(read(P/'cards.json'))

if __name__=='__main__':
 try:main_rotation()
 except Exception:
  (P/'rotation_error.txt').write_text(traceback.format_exc(),encoding='utf-8');write(P/'rotation_status.json',{'status':'failed'});raise
