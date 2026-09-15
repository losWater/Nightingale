from pathlib import Path
P=Path(__file__).resolve().parent
exec((P/'worker_base.py').read_text(encoding='utf-8'))
import psutil,time,statistics,os

def recipe(top,global_dup=0,hand=1.25,pair=0,balance=0,word=1):
 return dict(top=top,global_dup=global_dup,hand=hand,pair=pair,balance=balance,word=word)

def config(r,tag):
 c=read(P.parent/'23_重码保护范围试跑/configs'/f'{tag}_top{r["top"]}.json')
 o=c['optimization']['objective'];o['characters_full']['effective_duplication']=r['global_dup']
 for part in ['characters_full','characters_short']:
  for t in o[part]['tiers']:
   for k in ['fingering','weighted_fingering']:
    if k in t:t[k]=[x*r['hand']/1.25 for x in t[k]]
   if 'phonetic_shape_transition_equivalence'in t:t['phonetic_shape_transition_equivalence']*=r['hand']/1.25
 o['characters_short']['pair_equivalence']=r['pair'];o['characters_short']['key_distribution']=r['balance']
 o['character_word_collision']['weight']*=r['word']
 return c

def get_result(c):return read(P/'jobs'/c['id']/'round2.json')
def flatten(d):
 v={'综合分':d['score']['total'],'理论分':d['score']['theory']}
 for b in d['theory']['分段']:v[b['区间']+'·三码首选']=b['≤三码首选']
 v['理论有效重码率']=d['native']['characters_full']['effective_duplication']
 v['理论字词软碰撞']=d['native']['character_word_collision']['soft']
 for mode,b in d['benchmark']['实战'].items():
  for k,x in b.items():
   if isinstance(x,(int,float)) and not isinstance(x,bool):v[mode+'·'+k]=x
 return v

def report(cards):
 results=[];deltas={}
 for c in cards:
  f=P/'jobs'/c['id']/'round2.json'
  if not f.exists():continue
  d=read(f);v=flatten(d);base=read(P.parent/'21_手感权重微调/jobs'/f'{c["tag"]}_hand1.25/round2.json');bv=flatten(base)
  # Raw deltas are not automatically called improvements: e.g. left share has a midpoint target.
  deltas[c['id']]={k:{'基准':bv[k],'本次':x,'差值':x-bv[k]} for k,x in v.items() if k in bv}
  rows=d['theory']['分段'];results.append({'id':c['id'],'阶段':c['stage'],'参数':str(c['recipe']),'综合分':d['score']['total'],'相对原手感1.25':d['score']['total']-base['score']['total'],'前6000三码':sum(b['≤三码首选'] for b in rows[:5]),'纯字选重次数':d['benchmark']['实战']['纯单字']['字字选重次数'],'纯字字均当量':d['benchmark']['实战']['纯单字']['字均当量']})
 write(P/'每次得失明细.json',deltas);write(P/'运行结果.json',results)
 results.sort(key=lambda x:-x['综合分'])
 def table(rows):
  if not rows:return '<p>运行中</p>'
  ks=list(rows[0]);return '<table><tr>'+''.join('<th>'+html.escape(k)+'</th>' for k in ks)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(r[k]))+'</td>' for k in ks)+'</tr>' for r in rows)+'</table>'
 state=read(P/'status.json') if (P/'status.json').exists() else {}
 page='<!doctype html><meta charset="utf-8"><title>自动分批细化</title><style>body{font:16px system-ui;background:#f3f6fa;margin:30px;color:#213047}table{border-collapse:collapse}td,th{padding:8px;border:1px solid #cbd5e1}p{max-width:1100px;line-height:1.8}</style><h1>自动分批细化</h1><p>'+html.escape(str(state))+'</p><p>三阶段：重码范围与全域字频惩罚→围绕优胜配置微调手感/当量/热力/字词→前三种配置独立重复验证。每次5万步，所有字音、根集、简码、温度与最终评分不变。参数变化不会自动写入正式方案。只用同一第二轮一万句作开发评价，不能作为独立泛化证据。每次原始指标变化保存在“每次得失明细.json”，正负不等于统一好坏；左手负担应接近50%。前300有效选重非零者不参与自动晋级，但仍完整记录。</p><div style="overflow:auto">'+table(results)+'</div>'
 if (P/'阶段排名.json').exists():page+='<h2>阶段决策记录</h2><pre>'+html.escape(json.dumps(read(P/'阶段排名.json'),ensure_ascii=False,indent=2))+'</pre>'
 (P/'进度与结果.html').write_text(page,encoding='utf-8')

def run_one(c):
 if (P/'jobs'/c['id']/'round2.json').exists():return
 for attempt in range(2):
  deadline=time.time()+1800
  while psutil.virtual_memory().available<4*1024**3 or psutil.disk_usage(str(P)).free<12*1024**3:
   if time.time()>deadline:raise RuntimeError('资源不足持续30分钟，保留现场')
   time.sleep(15)
  with (P/(c['id']+f'_attempt{attempt}.log')).open('w',encoding='utf-8') as f:
   child=subprocess.Popen([sys.executable,str(P/'run.py'),'worker',c['id']],stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   try:rc=child.wait(timeout=5400)
   except subprocess.TimeoutExpired:
    proc=psutil.Process(child.pid)
    for sub in proc.children(recursive=True):
     try:sub.kill()
     except psutil.Error:pass
    child.kill();child.wait();raise RuntimeError('运行超时，已停止本任务进程树')
  if rc==0:return
 raise RuntimeError(c['id']+'两次失败')

def stage(number,recipes,repeats=1):
 cards=read(P/'cards.json') if (P/'cards.json').exists() else [];batch=[]
 for i,r in enumerate(recipes):
  for rep in range(repeats):
   for tag in ['A','D']:
    id=f's{number}_r{i}_{tag}_{rep}';path=P/'configs'/(id+'.json');c={'id':id,'stage':number,'recipe':r,'tag':tag,'steps':50000,'original_config':str(path),'label':id,'recipe_index':i}
    if not any(x['id']==id for x in cards):
     cfg=config(r,tag);write(path,cfg);cards.append(c)
    batch.append(c)
 write(P/'cards.json',cards)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  for f in concurrent.futures.as_completed([pool.submit(run_one,c) for c in batch]):
   f.result();write(P/'status.json',{'status':'running','stage':number,'completed':len(list((P/'jobs').glob('*/round2.json'))),'planned_so_far':len(cards),'pid':os.getpid()});report(cards)
 ranking=[]
 for i,r in enumerate(recipes):
  ds=[get_result(c) for c in batch if c['recipe_index']==i]
  eligible=all(next(t for t in d['native']['characters_full']['tiers'] if t['top']==300)['effective_duplication']==0 for d in ds)
  scores=[d['score']['total'] for d in ds];ranking.append({'recipe':r,'eligible':eligible,'scores':scores,'mean':statistics.mean(scores),'min':min(scores),'sd':statistics.pstdev(scores),'selection':statistics.mean(scores)-.25*statistics.pstdev(scores)})
 ranking.sort(key=lambda x:(x['eligible'],x['selection']),reverse=True)
 history=read(P/'阶段排名.json') if (P/'阶段排名.json').exists() else {};history[str(number)]=ranking;write(P/'阶段排名.json',history);report(cards)
 return ranking

def main():
 write(P/'status.json',{'status':'running','pid':os.getpid(),'stage':1})
 first=stage(1,[recipe(top,g) for top in [3000,6000] for g in [0,100,300]])
 eligible=[x for x in first if x['eligible']]
 if not eligible:raise RuntimeError('阶段一没有通过前300门槛的配置，需要审查，不自动放宽门槛')
 best=eligible[0]['recipe'];rs=[]
 for hand in [1,1.125,1.5]:rs.append({**best,'hand':hand})
 rs += [{**best,'pair':.5},{**best,'balance':.5},{**best,'word':1.25}]
 second=stage(2,rs)
 candidates=sorted([x for x in first+second if x['eligible']],key=lambda x:x['selection'],reverse=True)[:3]
 third=stage(3,[x['recipe'] for x in candidates],2)
 write(P/'最终建议.json',{'验证排名':third,'说明':'按独立重复阶段结果排名。保留所有收益与损失，不自动替换默认方案；未更改评分规则。'})
 write(P/'status.json',{'status':'complete','completed':len(list((P/'jobs').glob('*/round2.json'))),'stages':3,'pid':os.getpid()});report(read(P/'cards.json'))

if __name__=='__main__':
 if len(sys.argv)>1:worker(next(c for c in read(P/'cards.json') if c['id']==sys.argv[2]))
 else:
  try:main()
  except Exception:
   (P/'controller_error.txt').write_text(traceback.format_exc(),encoding='utf-8');write(P/'status.json',{'status':'failed','error':'见controller_error.txt','pid':os.getpid()});raise
