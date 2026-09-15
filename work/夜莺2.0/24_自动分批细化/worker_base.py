from pathlib import Path
import sys,copy,subprocess,concurrent.futures,html,traceback
P=Path(__file__).resolve().parent;T=P.parent/'15_自动晋级赛';sys.path.insert(0,str(T))
from common import *

def prepare():
 cards=[];audit=[]
 for tag,ident in [('A','g12_small_04'),('D','g02_random_03')]:
  base=read(T/'jobs'/ident/'search/run.json')
  for factor in [1,2]:
   cfg=copy.deepcopy(base);cfg['optimization']['metaheuristic']['parameters']['steps']=50000
   changes=[]
   def scale(d,path):
    if isinstance(d,dict):
     for k,v in d.items():
      if k in ['fingering','weighted_fingering']:
       for i,x in enumerate(v):
        if x:changes.append({'path':path+'/'+k+'/'+str(i),'old':x,'new':x*factor})
       d[k]=[x*factor for x in v]
      elif k in ['pair_equivalence','phonetic_shape_transition_equivalence','key_distribution'] and isinstance(v,(float,int)):
       if v:changes.append({'path':path+'/'+k,'old':v,'new':v*factor})
       d[k]=v*factor
      else:scale(v,path+'/'+k)
    elif isinstance(d,list):
     for i,v in enumerate(d):scale(v,path+'/'+str(i))
   for k in ['characters_full','characters_short']:scale(cfg['optimization']['objective'][k],k)
   check=copy.deepcopy(cfg)
   for change in changes:
    bits=change['path'].split('/');p=check['optimization']['objective']
    for bit in bits[:-1]:p=p[int(bit)] if isinstance(p,list) else p[bit]
    last=int(bits[-1]) if isinstance(p,list) else bits[-1];p[last]=change['old']
   expected=copy.deepcopy(base);expected['optimization']['metaheuristic']['parameters']['steps']=50000
   assert check==expected
   id=tag+'_hand'+str(factor);path=P/'configs'/(id+'.json');write(path,cfg)
   cards.append({'id':id,'original_config':str(path),'steps':50000,'baseline':ident,'label':f'{tag}起点 手感×{factor}','factor':factor})
   audit.append({'id':id,'changes':changes,'source_sha256':sha(T/'jobs'/ident/'search/run.json')})
 write(P/'cards.json',cards);write(P/'权重差异审计.json',audit);return cards

def worker(c):
 where=P/'jobs'/c['id'];where.mkdir(parents=True,exist_ok=True)
 if (where/'round2.json').exists():return
 source=(T/'worker.py').read_text(encoding='utf-8').split('def work(')[0]
 start=source.index(" cfg=read(F/'initial.json')");end=source.index(" cfg['optimization']['metaheuristic']['parameters']['steps']",start)
 source=source[:start]+" cfg=read(Path(card['original_config']));groups=sorted(k for k in cfg['form']['mapping'] if k.startswith('G'))\n"+source[end:]
 ns={'__file__':str(P/'run.py')};exec(source,ns);ns['SET']=copy.deepcopy(SET);ns['SET']['steps']=50000
 opt=ns['optimize'](c,where);assert read(where/'search/run.json')==read(c['original_config'])
 theory=theory_data(opt['native'],opt['code']);bench=bench_module(2,P/'practice',False)['run'](Path(opt['code']),c['id'])
 assert all(x['可计分'] and not x['缺字音字次'] for x in bench['实战'].values())
 write(where/'round2.json',{'card':c,'theory':theory,'benchmark':bench,'score':combine(theory,bench),'native':opt['native']})

