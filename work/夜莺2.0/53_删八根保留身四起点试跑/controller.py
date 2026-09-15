from common import *
import subprocess,psutil,shutil,traceback,msvcrt,html

STATE=ROOT/'status.json'
def status(stage,**kwargs):
 write(STATE,{'stage':stage,'updated':time.strftime('%Y-%m-%d %H:%M:%S'),'pid':os.getpid(),**kwargs})
 page='<meta charset="utf-8"><meta http-equiv="refresh" content="30"><title>夜莺自动晋级赛进度</title><style>body{font:18px system-ui;margin:40px;background:#f4f7fb;color:#234}td,th{padding:10px;text-align:left}pre{white-space:pre-wrap}</style><h1>夜莺2.0 · 自动晋级赛</h1><p>四种起点各5万步 → 两套固定语料评分 → 与未删根第一名对照</p><table>'+''.join('<tr><th>'+html.escape(str(k))+'</th><td>'+html.escape(str(v))+'</td></tr>' for k,v in read(STATE).items())+'</table><p>进度每30秒自动刷新；正常运行无需打开对话。</p>'
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
  message={'max_parallel':SET['max_parallel'],'completed_in_batch':completed,'batch_size':len(cards),'running':list(active),'pending_in_batch':len(queue),'free_memory_gb':round(free,2),'free_disk_gb':round(disk.free/2**30,1),'first_round_completed':len(list((ROOT/'jobs').glob('*/round1.json'))),'second_round_completed':len(list((ROOT/'jobs').glob('*/round2.json')))}
  status(f'round{roundno}',**message)
  with (ROOT/'resources.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'time':time.time(),**message})+'\n')
  # 紧急资源不足时终止本轮自有计算并自动降为单并发重试，不操作用户程序。
  if active and (free<2 or disk.free/2**30<12):
   SET['max_parallel']=1
   for proc,_,_,_ in active.values():safe_stop(proc.pid)
  if queue or active:time.sleep(15)
 return [read(ROOT/'jobs'/c['id']/f'round{roundno}.json') for c in cards]

def finish(finals,allrank):
 target=ROOT/'finalists';target.mkdir(exist_ok=True)
 pages=['<!doctype html><meta charset="utf-8"><title>夜莺2.0最终候选</title><style>body{font-family:system-ui;margin:30px;background:#f4f7fb;color:#243746}td,th{padding:8px;border:1px solid #bdcddd}table{border-collapse:collapse}.row{display:flex;gap:4px;margin:4px}.key{width:70px;padding:8px 2px;text-align:center;background:#e0ebf4}p{max-width:1100px;line-height:1.7}</style><h1>自动晋级赛 · 四个试跑结果</h1><p>四种起点各一次、当前均衡参数、主读音硬保护、统一5万步；四版全部进入第二轮同口径评分。第二轮换用无第一轮文本重叠的一万句，理论分保持不变。分数是冻结规则下的模拟分，非实际打字速度；上下文读音由固定词库和工具给出，仍非逐句人工校准。词词碰撞不直接扣冲突分，真实击键成本保留。没有发布或修改1.0。</p><table><tr><th>名次</th><th>编号</th><th>开局</th><th>理论</th><th>单字实战</th><th>字词实战</th><th>总分</th></tr>']
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
 write(ROOT/'四版排名.json',allrank);write(ROOT/'四版结果.json',finals)


def main():
 lock=(ROOT/'controller.lock').open('a+b');lock.write(b'0');lock.flush();lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
 try:
  seals=read(ROOT/'sealed_inputs.json')
  for p,digest in seals.items():assert sha(ROOT/p)==digest,('输入变化',p)
  status('starting');cards=read(ROOT/'cards.json');batch(cards,1);results=batch(cards,2);results.sort(key=lambda r:-r['score']['total'])
  finish(results,results)
  for r in results:
   src=Path(r['benchmark_path']).parent/'纯单字码表.txt';plain=[]
   for l in src.read_text(encoding='utf-8').splitlines():
    c,t=l.split('=',1);rank,ch=t.split(',',1);plain.append(ch+'\t'+c)
   out=ROOT/'普通码表';out.mkdir(exist_ok=True);(out/(r['id']+'.txt')).write_text('\n'.join(plain)+'\n',encoding='utf-8-sig')
  subprocess.run(['D:/nodejs/node.exe',str(ROOT/'evaluate.mjs')],cwd=ROOT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
  box=read(ROOT/'盒子分档对照.json');rows=[]
  before=read(ROOT.parent/'52_均衡参数512方案正式晋级赛/jobs/g06_large_01/round2.json')
  for r in [before,*results]:
   x=next(x for x in box if x['id']==r['id']);matrix=r['theory']['字词矩阵']['剔除有简码字音项'];red=sum(sum(v[:3]) for v in matrix[:2]);rows.append({'id':r['id'],'综合分':r['score']['total'],'常用区碰撞对':red,'盒子':x})
  write(ROOT/'汇总.json',rows)
  page='<meta charset="utf-8"><title>删根四起点对照</title><style>body{font:17px system-ui;margin:32px;background:#f4f7fb;color:#234}table{border-collapse:collapse}td,th{border:1px solid #abc;padding:12px}</style><h1>删八根、保留身 · 四起点试跑</h1><p>删除古、商、啇、向、向字框、囱字框、鹿、鬲。保留身、鹿旁、羊、南字心。沿用原分音字频，未混入di人工微调。相同5万步与原主读音保护。各起点只试一次，不作为稳定优劣结论。</p><table><tr><th>方案</th><th>综合分</th><th>盒子前1500简码数</th><th>1–300当量</th><th>301–500当量</th><th>501–1500当量</th><th>前1500当量</th><th>常用区字词冲突</th></tr>'
  for r in rows:
   x=r['盒子'];vals=[r['id'],f'{r["综合分"]:.4f}',x['short'],*[f'{v["eq"]:.5f}' for v in x['bands'][:3]],f'{x["eq1500"]:.5f}',r['常用区碰撞对']];page+='<tr>'+''.join('<td>'+str(v)+'</td>' for v in vals)+'</tr>'
  page+='</table><p>综合分使用第二轮固定一万句；当量列使用形码盒子默认字频理论口径。常用区：退火字音项前1500×词前10000，剔除有简码项。</p><p><a href="最终候选报告.html">实战与热力图</a></p>'
  (ROOT/'对照结果.html').write_text(page,encoding='utf-8')
  status('complete',completed=4,report=str(ROOT/'对照结果.html'))
 except Exception:
  (ROOT/'controller_error.txt').write_text(traceback.format_exc(),encoding='utf-8');status('needs_attention');raise
if __name__=='__main__':main()
