from pathlib import Path
P=Path(__file__).resolve().parent
exec((P/'base_snapshot.py').read_text(encoding='utf-8'))

def prepare():
 cards=[];audit=[]
 for tag in ['A','D']:
  base=read(P.parent/'21_手感权重微调/configs'/f'{tag}_hand1.25.json')
  for top in [500,1000,1500,3000,6000]:
   cfg=copy.deepcopy(base);tiers=cfg['optimization']['objective']['characters_full']['tiers']
   old=next(t for t in tiers if t['top']==300);assert old['effective_duplication']==8
   target=next((t for t in tiers if t['top']==top),None)
   if target is None:
    target=copy.deepcopy(old);target['top']=top;tiers.append(target);tiers.sort(key=lambda t:t['top'])
   old['effective_duplication']=0;target['effective_duplication']=8*top/300
   check=copy.deepcopy(cfg);check['optimization']['objective']['characters_full']['tiers']=copy.deepcopy(base['optimization']['objective']['characters_full']['tiers']);assert check==base
   id=f'{tag}_top{top}';f=P/'configs'/(id+'.json');write(f,cfg)
   cards.append({'id':id,'original_config':str(f),'steps':50000,'baseline':tag,'label':f'{tag}·保护前{top}','top':top})
   audit.append({'id':id,'保护范围':top,'分档权重':8*top/300,'每个有效选重惩罚':8/300,'前300重复加罚':False,'原配置SHA256':sha(P.parent/'21_手感权重微调/configs'/f'{tag}_hand1.25.json')})
 write(P/'cards.json',cards);write(P/'差异审计.json',audit);return cards

original_worker=worker
def worker(c):
 original_worker(c)
 d=read(P/'jobs'/c['id']/'round2.json');tiers=d['native']['characters_full']['tiers']
 assert any(t['top']==c['top'] and t['effective_duplication'] is not None for t in tiers)

def report():
 ds=[read(f) for f in sorted((P/'jobs').glob('*/round2.json'))]
 for tag in ['A','D']:
  d=read(P.parent/'21_手感权重微调/jobs'/f'{tag}_hand1.25/round2.json');d['card']={**d['card'],'label':tag+'·保护前300（既有）','top':300,'baseline':tag};ds.append(d)
 ds.sort(key=lambda d:(d['card']['baseline'],d['card']['top']))
 rows=[]
 for d in ds:
  r={'方案':d['card']['label'],'固定标准综合分':d['score']['total'],'前1500≤三码':sum(x['≤三码首选'] for x in d['theory']['分段'][:3]),'前6000≤三码':sum(x['≤三码首选'] for x in d['theory']['分段'][:5])}
  # Recompute all cutoffs from actual emitted five-column table, including baseline's missing 1000 tier.
  if d['card']['top']==300:path=P.parent/'21_手感权重微调/jobs'/d['card']['id']/'optimized.json'
  else:path=P/'jobs'/d['card']['id']/'optimized.json'
  opt=read(path);es=yload(F/'elements.yaml');codes=[l.split('\t') for l in Path(opt['code']).read_text(encoding='utf-8').splitlines()]
  part=[(e,c) for e,c in zip(es,codes) if len(e['词'])==1];assert len(part)==8454
  for top in [300,500,1000,1500,3000,6000]:
   r[f'前{top}有效全码选重项数']=sum(len(c[3])==4 and int(c[2])>0 for e,c in part[:top])
  for mode,b in d['benchmark']['实战'].items():
   for k in ['每字击键','字均当量','键均当量','字字选重次数','字字选重率_单字上屏','字词增量受影响率','大跨排率','小跨排率','左手占比_不含空格','最高单键占比_不含空格']:r[mode+'·'+k]=b[k]
  rows.append(r)
 write(P/'完整指标.json',rows)
 def table(rs):
  if not rs:return ''
  keys=list(rs[0]);return '<table><tr>'+''.join('<th>'+html.escape(k)+'</th>' for k in keys)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(f'{r[k]:.6f}' if isinstance(r[k],float) else str(r[k]))+'</td>' for k in keys)+'</tr>' for r in rs)+'</table>'
 page='<!doctype html><meta charset="utf-8"><title>重码保护范围试跑</title><style>body{font:16px system-ui;background:#f3f6fa;color:#213047;margin:30px}table{border-collapse:collapse;background:white}th,td{padding:9px;border:1px solid #cbd5e1}p{max-width:1100px;line-height:1.8}</style><h1>重码保护能推进到哪里</h1><p>手感×1.25，两原始起点，每格50000步。前300对照沿用上一轮；新增前500、1000、1500、3000、6000。分档惩罚按 N×8/300 设置，每个有效选重单位惩罚恒定，旧前300项置零避免重复计罚。其余权重、温度、输入及最终计分不变。保护是软惩罚，不是零重码硬保证；每格一次、随机流未固定，只作探索。范围指既定字频排序的字音项。</p><p>有效全码选重项数按无简码且全码非首选统计，不是字对数；同一万句的实战选重另列。各方案源码表及完整分段矩阵保存于jobs。需同时关注前300有无退步，不能只看扩大范围后的总数。</p><div style="overflow:auto">'+table(rows)+'</div>'
 (P/'保护范围对照.html').write_text(page,encoding='utf-8')

if __name__=='__main__':
 if len(sys.argv)>1:worker(next(c for c in read(P/'cards.json') if c['id']==sys.argv[2]))
 else:
  cards=prepare();done=0;errors=[];write(P/'status.json',{'status':'running','completed':0,'total':10});report()
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
   for f in concurrent.futures.as_completed([pool.submit(launch,c) for c in cards]):
    try:f.result()
    except Exception as e:errors.append(str(e))
    done+=1;write(P/'status.json',{'status':'running','completed':done,'total':10,'errors':errors});report()
  write(P/'status.json',{'status':'complete' if not errors else 'failed','completed':done,'total':10,'errors':errors});report()
