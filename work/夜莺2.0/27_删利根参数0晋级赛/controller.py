from common import *
import subprocess,psutil,shutil,traceback,msvcrt,html

STATE=ROOT/'status.json'
def status(stage,**kwargs):
 write(STATE,{'stage':stage,'updated':time.strftime('%Y-%m-%d %H:%M:%S'),'pid':os.getpid(),**kwargs})
 page='<meta charset="utf-8"><meta http-equiv="refresh" content="30"><title>夜莺自动晋级赛进度</title><style>body{font:18px system-ui;margin:40px;background:#f4f7fb;color:#234}td,th{padding:10px;text-align:left}pre{white-space:pre-wrap}</style><h1>夜莺2.0 · 自动晋级赛</h1><p>第一轮512次 → 128个晋级 → 第二轮换语料 → 最终5个候选</p><table>'+''.join('<tr><th>'+html.escape(str(k))+'</th><td>'+html.escape(str(v))+'</td></tr>' for k,v in read(STATE).items())+'</table><p>进度每30秒自动刷新；正常运行无需打开对话。</p>'
 if (ROOT/'最终候选报告.html').exists():page+='<p><a href="最终候选报告.html">查看最终候选报告</a></p>'
 (ROOT/'进度.html').write_text(page,encoding='utf-8')
def safe_stop(pid):
 try:
  process=psutil.Process(pid);children=process.children(recursive=True)
  for child in reversed(children):
   try:child.terminate()
   except psutil.Error:pass
  process.terminate()
 except psutil.Error:pass

def batch(cards,roundno):
 queue=[c for c in cards if not (ROOT/'jobs'/c['id']/f'round{roundno}.json').exists()];active={};attempts=Counter()
 progress=ROOT/f'round{roundno}_attempts.json'
 if progress.exists():attempts.update(read(progress))
 while queue or active:
  mem=psutil.virtual_memory();disk=shutil.disk_usage(ROOT);free=mem.available/2**30
  for id,(proc,card,started,handle) in list(active.items()):
   if proc.poll() is None and time.time()-started>SET['max_task_hours']*3600:safe_stop(proc.pid)
   if proc.poll() is not None:
    handle.close();del active[id]
    if proc.returncode!=0 or not (ROOT/'jobs'/id/f'round{roundno}.json').exists():
     if attempts[id]>=SET['max_attempts']:
      for other,_,_,_ in active.values():safe_stop(other.pid)
      raise RuntimeError(f'{id} round {roundno} 自动重试耗尽')
     queue.insert(0,card)
  if queue and len(active)<SET['max_parallel'] and free>=SET['launch_memory_gb'] and disk.free/2**30>=SET['min_disk_gb']:
   card=queue.pop(0);id=card['id'];attempts[id]+=1;write(progress,dict(attempts));folder=ROOT/'jobs'/id;folder.mkdir(parents=True,exist_ok=True)
   handle=(folder/f'round{roundno}_attempt{attempts[id]}.log').open('w',encoding='utf-8')
   proc=subprocess.Popen([sys.executable,str(ROOT/'worker.py'),id,'--round',str(roundno)],cwd=ROOT,stdout=handle,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   active[id]=(proc,card,time.time(),handle)
  completed=sum((ROOT/'jobs'/c['id']/f'round{roundno}.json').exists() for c in cards)
  message={'completed_in_batch':completed,'batch_size':len(cards),'running':list(active),'pending_in_batch':len(queue),'free_memory_gb':round(free,2),'free_disk_gb':round(disk.free/2**30,1),'first_round_completed':len(list((ROOT/'jobs').glob('*/round1.json'))),'second_round_completed':len(list((ROOT/'jobs').glob('*/round2.json')))}
  status(f'round{roundno}',**message)
  with (ROOT/'resources.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'time':time.time(),**message})+'\n')
  # 紧急资源不足时终止本轮自有计算并自动降为单并发重试，不操作用户程序。
  if active and (free<.35 or disk.free/2**30<3):
   SET['max_parallel']=1
   for proc,_,_,_ in active.values():safe_stop(proc.pid)
  if queue or active:time.sleep(15)
 return [read(ROOT/'jobs'/c['id']/f'round{roundno}.json') for c in cards]

def finish(finals,allrank):
 target=ROOT/'finalists';target.mkdir(exist_ok=True)
 pages=['<!doctype html><meta charset="utf-8"><title>夜莺2.0最终候选</title><style>body{font-family:system-ui;margin:30px;background:#f4f7fb;color:#243746}td,th{padding:8px;border:1px solid #bdcddd}table{border-collapse:collapse}.row{display:flex;gap:4px;margin:4px}.key{width:70px;padding:8px 2px;text-align:center;background:#e0ebf4}p{max-width:1100px;line-height:1.7}</style><h1>自动晋级赛 · 最终5个候选</h1><p>32组各16次、参数0、统一5万步；每组4名进入第二轮。第二轮换用无第一轮文本重叠的一万句，理论分保持不变。分数是冻结规则下的模拟分，非实际打字速度；上下文读音由固定词库和工具给出，仍非逐句人工校准。词词碰撞不直接扣冲突分，真实击键成本保留。没有发布或修改1.0。</p><table><tr><th>名次</th><th>编号</th><th>开局</th><th>理论</th><th>单字实战</th><th>字词实战</th><th>总分</th></tr>']
 for i,r in enumerate(finals,1):
  folder=target/f'{i:02d}_{r["id"]}';folder.mkdir(exist_ok=True);job=ROOT/'jobs'/r['id'];opt=read(job/'optimized.json')
  shutil.copyfile(job/'final_config.json',folder/'最终布局配置.json');shutil.copyfile(opt['code'],folder/'单字_Chai五列表.txt');shutil.copyfile(job/'theory.json',folder/'理论分档与碰撞.json')
  roots=read(F/'当前完整根表.json')['根组']
  (folder/'根组键位表.md').write_text('|根组|键位|包含根形|\n|---|---|---|\n'+''.join('|'+g['根组']+'|'+opt['layout'][f'G{g["序号"]:03d}']+'|'+ '、'.join(g['根形'])+'|\n' for g in roots),encoding='utf-8')
  b=read(r['benchmark_path']);write(folder/'评分与实战.json',{'晋级结果':r,'实战':b})
  benchdir=Path(r['benchmark_path']).parent
  for n in ['纯单字码表.txt','无简词字词码表.txt']:shutil.copyfile(benchdir/n,folder/n)
  plain=[]
  for line in (benchdir/'纯单字码表.txt').read_text(encoding='utf-8').splitlines():
   code,tail=line.split('=',1);rank,ch=tail.split(',',1);assert len(ch)==1;plain.append(ch+'\t'+code+'\n')
  assert len({line.split('\t')[0] for line in plain})==8105
  (folder/'普通纯单字表.txt').write_text(''.join(plain),encoding='utf-8')
  sc=r['score'];pages.append(f'<tr><td>{i}</td><td>{r["id"]}</td><td>{r["kind"]}</td><td>{sc["theory"]:.4f}</td><td>{sc["practice"]["纯单字"]["score"]:.4f}</td><td>{sc["practice"]["无简词字词"]["score"]:.4f}</td><td>{sc["total"]:.4f}</td></tr>')
 pages.append('</table>')
 for r in finals:
  b=read(r['benchmark_path']);pages.append('<h2>'+r['id']+'</h2>')
  for mode,d in b['实战'].items():
   pages.append(f'<h3>{mode}</h3><p>每字击键 {d["每字击键"]:.4f}；键均当量 {d["键均当量"]:.4f}；字均当量 {d["字均当量"]:.4f}；字词增量影响率 {d["字词增量受影响率"]:.4%}</p>')
   for title,counts in [('全部按键',d['按键次数']),('编码键',d['编码键热力'])]:
    pages.append('<h4>'+title+'</h4>');total=sum(counts.values())
    for row in ['1234567890-=','qwertyuiop[]',"asdfghjkl;'",'zxcvbnm,./',' ']:
     pages.append('<div class="row">')
     for k in row:
      n=counts.get(k,0);v=n/total;color=f'hsl(208 65% {98-55*min(v/.1,1):.1f}%)'
      pages.append('<div class="key" style="background:'+color+'">'+html.escape('空格' if k==' ' else k)+f'<br>{v:.2%}<br>{n}</div>')
     pages.append('</div>')
 (ROOT/'最终候选报告.html').write_text(''.join(pages),encoding='utf-8')
 write(ROOT/'最终128排名.json',allrank);write(ROOT/'最终五名.json',finals)

def main():
 lock=(ROOT/'controller.lock').open('a+b');lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
 try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 except OSError:raise RuntimeError('总控已运行，拒绝重复启动')
 psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
 try:
  status('preparing')
  for n,h in read(ROOT/'sealed_inputs.json').items():
   assert sha(ROOT/n)==h,('输入指纹不符',n)
  prepare_first();cards=read(ROOT/'cards.json');promoted=[];seen=set()
  for group in range(1,SET['groups']+1):
   batchcards=[c for c in cards if c['group']==group];results=batch(batchcards,1);ranked=sorted(results,key=lambda r:(-r['score']['total'],r['id']));chosen=[]
   for r in ranked:
    native=read(ROOT/'jobs'/r['id']/'optimized.json')['native']
    if next(t for t in native['characters_full']['tiers'] if t['top']==300)['effective_duplication']!=0:continue
    if r['layout_hash'] not in seen:chosen.append(r);seen.add(r['layout_hash'])
    if len(chosen)==SET['promote']:break
   write(ROOT/f'group_{group:02d}_selection.json',{'ranked':[r['id'] for r in ranked],'selected':[r['id'] for r in chosen],'rule':'前300有效重码为0，综合分降序、全赛去重；不足4名停止，不放宽门槛'})
   if len(chosen)<SET['promote']:raise RuntimeError(f'组{group}不足4个不同布局；需要处理重复布局')
   promoted.extend(chosen);write(ROOT/f'group_{group:02d}_ranking.json',ranked);write(ROOT/'晋级128名单_进行中.json',promoted)
  assert len(promoted)==128;write(ROOT/'晋级128名单.json',promoted)
  status('preparing_round2');prepare_second()
  ids={r['id'] for r in promoted};allrank=sorted(batch([c for c in cards if c['id'] in ids],2),key=lambda r:(-r['score']['total'],r['id']))
  finals=allrank[:SET['finalists']]
  # 五名补存详细逐句轨迹，无需再次退火。
  from worker import work
  for r in finals:
   card=next(c for c in cards if c['id']==r['id']);detailed=work(card,2,True);assert abs(detailed['score']['total']-r['score']['total'])<1e-9
  finish(finals,allrank);status('complete',first_round_completed=512,second_round_completed=128,finalists=[r['id'] for r in finals],report=str(ROOT/'最终候选报告.html'))
 except Exception:
  error=traceback.format_exc();(ROOT/'controller_error.txt').write_text(error,encoding='utf-8');status('needs_attention',error=error[-3000:]);raise
if __name__=='__main__':main()
