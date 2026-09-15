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

def report():
 ds=[read(f) for f in sorted((P/'jobs').glob('*/round2.json'))];rows=[]
 for d in ds:
  r={'方案':d['card']['label'],'固定标准综合分':d['score']['total'],'前1500≤三码':sum(x['≤三码首选'] for x in d['theory']['分段'][:3]),'前6000≤三码':sum(x['≤三码首选'] for x in d['theory']['分段'][:5])}
  for mode,b in d['benchmark']['实战'].items():
   for k in ['每字击键','字均当量','键均当量','大跨排率','小跨排率','字字选重率_单字上屏','字词增量受影响率','左手占比_不含空格','最高单键占比_不含空格','小指占比_不含空格','同键三连率','同指三连率']:r[mode+'·'+k]=b[k]
  rows.append(r)
 write(P/'完整指标.json',rows)
 def table(rs):
  if not rs:return '<p>正在运行</p>'
  keys=list(rs[0]);return '<table><tr>'+''.join('<th>'+html.escape(k)+'</th>' for k in keys)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(f'{r[k]:.6f}' if isinstance(r[k],float) else str(r[k]))+'</td>' for k in keys)+'</tr>' for r in rs)+'</table>'
 small=[{k:v for k,v in r.items() if k in ['方案','固定标准综合分','前1500≤三码','前6000≤三码','纯单字·每字击键','纯单字·字均当量','纯单字·大跨排率','纯单字·小跨排率','无简词字词·字词增量受影响率']} for r in rows]
 page='<!doctype html><meta charset="utf-8"><title>手感权重五万步对照</title><style>body{font:16px system-ui;background:#f3f6fa;color:#213047;margin:32px}table{border-collapse:collapse;background:white}td,th{padding:10px;border:1px solid #cbd5e1}p{line-height:1.8;max-width:1100px}</style><h1>手感权重五万步对照</h1><p>两种原始起点，各跑原权重与手感×2，每次50000步。只放大既有非零手感权重：分层大跨排110→220、小跨排20→40、全码音形换手0.25→0.5。三码、单字重码、字词碰撞、初终温度、根集、字频、简码规则均不变。当量和热力原目标为零，仍保留零；完整实战复测。用固定评分标准、同一第二轮一万句比较，不比较不同权重下的退火总分。原生随机流未固定，每格一次，只作趋势参考。</p>'+table(small)+'<h2>全部指标（可横向滚动）</h2><div style="overflow:auto">'+table(rows)+'</div>'
 for d in ds:page+='<h2>'+html.escape(d['card']['label'])+'：三码分段</h2>'+table(d['theory']['分段'])+'<h3>字词冲突矩阵</h3><pre>'+html.escape(json.dumps(d['theory']['字词矩阵'],ensure_ascii=False,indent=2))+'</pre>'
 (P/'手感权重对照.html').write_text(page,encoding='utf-8')

def launch(c):
 with (P/(c['id']+'.log')).open('w',encoding='utf-8') as f:
  p=subprocess.run([sys.executable,str(P/'run.py'),'worker',c['id']],stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 if p.returncode:raise RuntimeError(c['id']+'失败，详见日志')

if __name__=='__main__':
 if len(sys.argv)>1:worker(next(c for c in read(P/'cards.json') if c['id']==sys.argv[2]))
 else:
  cards=prepare();errors=[];done=0;write(P/'status.json',{'status':'running','completed':0,'total':4});report()
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
   for f in concurrent.futures.as_completed([pool.submit(launch,c) for c in cards]):
    try:f.result()
    except Exception as e:errors.append(str(e))
    done+=1;write(P/'status.json',{'status':'running','completed':done,'total':4,'errors':errors});report()
  write(P/'status.json',{'status':'complete' if not errors else 'failed','completed':done,'total':4,'errors':errors});report()
