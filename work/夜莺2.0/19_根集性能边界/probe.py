from pathlib import Path
import sys,json,copy,subprocess,concurrent.futures,time,traceback,html,hashlib
P=Path(__file__).resolve().parent;T=P.parent/'15_自动晋级赛';sys.path.insert(0,str(T))
from common import *

def bounds():
 es=yload(F/'elements.yaml'); es=[e for e in es if len(e['词'])==1]
 ds=sorted((T/'finalists').iterdir());tables=[]
 for d in ds:
  raw=[l.split('\t') for l in (d/'单字_Chai五列表.txt').read_text(encoding='utf-8').splitlines()]
  rows=[r for r in raw if len(r[0])==1];assert len(rows)==len(es)
  assert all(e['词']==r[0] for e,r in zip(es,rows))
  tables.append(rows)
 short={i for i,r in enumerate(tables[0]) if len(r[3])<=2 and int(r[4])==0}
 assert all(short=={i for i,r in enumerate(rows) if len(r[3])<=2 and int(r[4])==0} for rows in tables)
 out=[]
 for n in [300,500,1500,3000,6000,8454]:
  by=defaultdict(dict);fixed=0;fw=0
  for i,e in enumerate(es[:n]):
   if i in short:fixed+=1;fw+=e['频率'];continue
   seq=e['元素序列'];sy=tuple(x['element'] for x in seq[:2]);head=seq[2]['element']
   by[sy][head]=max(by[sy].get(head,0),e['频率'])
  distinct=sum(len(d) for d in by.values());upper=fixed+sum(min(26,len(d)) for d in by.values())
  den=sum(e['频率'] for e in es[:n]);wup=fw+sum(sum(sorted(d.values(),reverse=True)[:26]) for d in by.values())
  actual=[sum(len(r[3])<=3 and int(r[4])==0 for r in rows[:n]) for rows in tables]
  tails=defaultdict(lambda:defaultdict(list))
  for i,e in enumerate(es[:n]):
   if i in short:continue
   seq=tuple(x['element'] for x in e['元素序列']);tails[seq[:3]][seq[3]].append(e['频率'])
  unavoidable=0;unavoidable_weight=0
  for head,ts in tails.items():
   residual=[v for vs in ts.values() for v in sorted(vs,reverse=True)[1:]]
   unavoidable+=max(0,len(residual)-1)
   unavoidable_weight+=sum(residual)-max(residual,default=0)
  assert all(x<=upper for x in actual)
  out.append({'范围':n,'固定一二简':fixed,'根组同首不可避免退四':n-fixed-distinct,'26键附加容量损失':fixed+distinct-upper,'三码首选数量上界':upper,'加权覆盖上界':wup/den if den else None,'五候选最佳数量':max(actual),'与上界差':upper-max(actual),'单字非首选项数下界':unavoidable,'单字非首选频次下界':unavoidable_weight})
 collisions=defaultdict(list)
 for i,e in enumerate(es):
  if i not in short:collisions[tuple(x['element'] for x in e['元素序列'])].append({'排名':i+1,'字':e['词'],'拼音':e['拼音'],'频次':e['频率']})
 write(P/'理论边界.json',{'口径':'固定现有一二简所有者；各音码独立给首根分配26键，放松全局同根同键约束。上界不是可达值，各范围独立。','分段累计':out,'输入SHA256':sha(F/'elements.yaml'),'固定一二简数量':len(short)})
 names={'G%03d'%r['序号']:r['根组'] for r in read(F/'当前完整根表.json')['根组']}
 heads=defaultdict(list)
 for i,e in enumerate(es):
  if i in short:continue
  seq=e['元素序列'];key=tuple(x['element'] for x in seq[:3]);heads[key].append({'排名':i+1,'字':e['词'],'拼音':e['拼音'],'频次':e['频率']})
 blocked=[{'音码':''.join(k[2:] for k in key[:2]),'首根组':names[key[2]],'前三百冲突字':[r['字'] for r in vs if r['排名']<=300],'前1500至少退四':max(0,sum(r['排名']<=1500 for r in vs)-1),'全表至少退四':len(vs)-1,'字音项':vs} for key,vs in heads.items() if len(vs)>1]
 blocked.sort(key=lambda x:(-x['前1500至少退四'],-x['全表至少退四']))
 write(P/'根集不可消除的三码冲突.json',blocked)
 return out

GOALS=['three','cross','char_dup','pair','large_cross','small_cross','balance','separation','length','pinky']
LABELS={'three':'三码数量','cross':'字词碰撞','char_dup':'有效单字重码','pair':'键对当量','large_cross':'同指大跨排','small_cross':'同指小跨排','balance':'键盘分布','separation':'音形换手','length':'加权编码长度','pinky':'小指干扰'}

def prepare():
 cards=[]
 for goal in GOALS:
  for kind in ['champion','random']:
   ident=goal+'_'+kind; cfg=read(T/'jobs/g12_small_04/final_config.json')
   if kind=='random':
    rng=random.Random(20260912+GOALS.index(goal))
    for k in cfg['form']['mapping']:
     if k.startswith('G'):cfg['form']['mapping'][k]=rng.choice('abcdefghijklmnopqrstuvwxyz')
   # Keep all metric outputs present, zero only their objective coefficients.
   obj=cfg['optimization']['objective']
   def zero(d):
    for k,v in d.items():
     if k in ['top','length']:continue
     if isinstance(v,dict):zero(v)
     elif isinstance(v,list):
      if all(isinstance(x,(int,float)) for x in v):d[k]=[0.0]*len(v)
      else:
       for x in v:
        if isinstance(x,dict):zero(x)
     elif isinstance(v,(int,float)):d[k]=0.0
   saved=copy.deepcopy(obj['character_word_collision']);obj.pop('character_word_collision');zero(obj);saved['weight']=0;obj['character_word_collision']=saved
   s=obj['characters_short'];f=obj['characters_full']
   if goal=='three':
    for tier in s['tiers']:
     if tier['top']==6000:tier['levels']=[{'length':3,'frequency':-1.0}]
   elif goal=='cross':saved['weight']=1
   elif goal=='char_dup':f['effective_duplication']=1
   elif goal=='pair':s['pair_equivalence']=1
   elif goal in ['large_cross','small_cross']:s['fingering'][1 if goal=='large_cross' else 2]=1
   elif goal=='balance':s['key_distribution']=1
   elif goal=='separation':f['phonetic_shape_transition_equivalence']=1
   elif goal=='length':s['levels']=[{'length':i,'frequency':float(i)} for i in [1,2,3,4]]
   elif goal=='pinky':s['fingering'][3]=1
   cfg['optimization']['metaheuristic']['parameters']={'steps':20000,'t_max':.02,'t_min':.00001}
   path=P/'configs'/(ident+'.json');write(path,cfg)
   cards.append({'id':ident,'goal':goal,'kind':kind,'config':str(path)})
 write(P/'cards.json',cards);return cards

def worker(card):
 where=P/'jobs'/card['id'];where.mkdir(parents=True,exist_ok=True)
 if (where/'result.json').exists():return
 source=(T/'worker.py').read_text(encoding='utf-8').split('def work(')[0]
 start=source.index(" cfg=read(F/'initial.json')");end=source.index(" cfg['optimization']['metaheuristic']['parameters']['steps']",start)
 source=source[:start]+" cfg=read(Path(card['config']));groups=sorted(k for k in cfg['form']['mapping'] if k.startswith('G'))\n"+source[end:]
 ns={'__file__':str(P/'probe.py')};exec(source,ns);ns['SET']=copy.deepcopy(SET);ns['SET']['steps']=20000
 opt=ns['optimize'](card,where)
 theory=theory_data(opt['native'],opt['code']);bench=bench_module(2,P/'practice',False)['run'](Path(opt['code']),card['id'])
 write(where/'result.json',{'id':card['id'],'goal':card['goal'],'native_score':opt['native_score'],'native':opt['native'],'theory':theory,'benchmark':bench,'score':combine(theory,bench)})

def report():
 rows=[]
 for f in sorted((P/'jobs').glob('*/result.json')):
  d=read(f);b=d['benchmark']['实战'];pure=b['纯单字'] if '纯单字'in b else next(iter(b.values()))
  rows.append({'方案':d['id'],'目标':LABELS[d['goal']],'目标函数值':d['native_score'],'前6000三码首选':sum(x['≤三码首选'] for x in d['theory']['分段'][:5]),'综合分':d['score']['total'],'纯字每字击键':pure['每字击键'],'纯字键均当量':pure['键均当量'],'纯字字均当量':pure['字均当量']})
 write(P/'单项结果.json',rows)
 detailed=[]
 allresults=[read(f) for f in sorted((P/'jobs').glob('*/result.json'))]
 for candidate in ['g12_small_04','g12_large_03','g15_small_01','g02_random_03','g13_random_04']:
  allresults.append({'id':'原候选_'+candidate,'native':read(T/'jobs'/candidate/'optimized.json')['native'],'benchmark':read(T/'round2/results'/candidate/'结果.json')})
 for d in allresults:
  native=d['native'];short=native['characters_short'];full=native['characters_full']
  r={'方案':d['id'],'理论有效重码率':full['effective_duplication'],'理论字词碰撞软值':native['character_word_collision']['soft'],'理论键对当量':short['pair_equivalence'],'理论大跨排':short['fingering'][1],'理论小跨排':short['fingering'][2],'理论分布损失':short['key_distribution_loss']}
  for key in ['键均当量','字均当量']:r['理论46键·'+key]=d['benchmark']['理论当量_统一46键表'][key]
  for mode,b in d['benchmark']['实战'].items():
   for key in ['每字击键','键均当量','字均当量','字字选重率_单字上屏','字词增量受影响率','同键连击率','大跨排率','小跨排率','同键三连率','同键四连率','同指三连率','同指四连率','左手占比_不含空格','小指占比_不含空格','最高单键占比_不含空格','最高单指占比_不含空格']:
    r[mode+'·'+key]=b[key]
  detailed.append(r)
 write(P/'完整指标对照.json',detailed)
 envelope=[]
 if detailed:
  for k in list(detailed[0])[1:]:
   def loss(x):return abs(x[k]-.5) if '左手占比'in k else x[k]
   base=min((r for r in detailed if r['方案'].startswith('原候选')),key=loss)
   best=min(detailed,key=loss)
   envelope.append({'指标':k,'原五候选最好':base[k],'本轮连同基准最好':best[k],'对应方案':best['方案']})
 write(P/'各指标已知最好值.json',envelope)
 def table(rs):
  if not rs:return '<p>正在计算</p>'
  keys=list(rs[0]);return '<table><tr>'+''.join('<th>'+html.escape(k)+'</th>' for k in keys)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in keys)+'</tr>' for r in rs)+'</table>'
 text='''<!doctype html><meta charset="utf-8"><title>根集性能边界</title><style>body{font:16px system-ui;margin:40px;background:#f4f7fb;color:#213047}table{border-collapse:collapse;background:white;margin:24px 0}td,th{padding:10px;border:1px solid #cbd5e1}p{max-width:1000px;line-height:1.8}</style><h1>根集性能边界：理论上界与单项探测</h1><p>这不是综合候选排名。理论上界放松了全局同根同键约束；单项探测仅为可达成绩，不能证明全局最优，也不建议作为成品使用。每项采用冠军起点和随机起点各一次、2万步，统一探索温度0.02至0.00001，尚未逐项目校准温度或验证收敛。所有方案重跑同一第二轮一万句，并保留完整理论、热力与实战数据。</p><p>三码上界固定现有423个一二简所有者，按音码与首根组计算；各累计范围独立最大化，不保证同时达到。字词冲突最低不能小于0；各手感事件率最低0，但双拼固定且所有根共用布局，因此零不等于可达。单项探测会显示改善一种指标时其他指标付出的代价。</p>'''
 text+='<h2>三码与单字重码理论边界</h2>'+table(read(P/'理论边界.json')['分段累计'])+'<p>单字非首选项数下界：先让每个首根组独享一个键、每个末根组独享一个键；同音首末组仍相同的项目中，每组保留一个全码首选，再允许每个首根组用一个三简救出一项。剩余项目必然无法全部首选。它统计项目数，不是冲突对数；实际26键只能进一步增加冲突。</p><h2>各指标已知最好值（不能拼成同一布局）</h2>'+table(envelope)+'<h2>单项探测结果</h2>'+table(rows)+'<h2>完整理论及双模式实战指标</h2><p>横向滚动查看所有指标。两次单项试跑只是探索，不叫已证明上限。每次完整按键热力、分档字词碰撞矩阵和码表存放在对应jobs与practice目录。</p><div style="overflow:auto">'+table(detailed)+'</div>'
 (P/'性能边界.html').write_text(text,encoding='utf-8')

def main():
 bounds();cards=prepare();write(P/'status.json',{'status':'running','total':len(cards),'completed':0});report()
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  futures={pool.submit(run_process,c):c for c in cards}
  errors=[];done=0
  for f in concurrent.futures.as_completed(futures):
   c=futures[f]
   try:f.result()
   except Exception as e:errors.append({'id':c['id'],'error':str(e)})
   done+=1;write(P/'status.json',{'status':'running','total':len(cards),'completed':done,'errors':errors});report()
 write(P/'status.json',{'status':'complete' if not errors else 'failed','total':len(cards),'completed':done,'errors':errors});report()

def run_process(c):
 with (P/(c['id']+'.log')).open('w',encoding='utf-8') as log:
  r=subprocess.run([sys.executable,str(P/'probe.py'),'worker',c['id']],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 if r.returncode:raise RuntimeError('worker failed; see '+c['id']+'.log')

if __name__=='__main__':
 if len(sys.argv)>1:worker(next(c for c in read(P/'cards.json') if c['id']==sys.argv[2]))
 else:main()
