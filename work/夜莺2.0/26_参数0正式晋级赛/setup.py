from pathlib import Path
import json,shutil,hashlib,py_compile
P=Path(__file__).resolve().parent;T=P.parent/'15_自动晋级赛';F=P/'frozen'
if (P/'sealed_inputs.json').exists():raise RuntimeError('已冻结，不重复初始化')
F.mkdir(exist_ok=True)
for f in (T/'frozen').iterdir():
 if f.is_file():shutil.copy2(f,F/f.name)
shutil.copytree(T/'frozen/round1',F/'round1',dirs_exist_ok=True)
# Vendor is small and frozen locally; raw corpora remain read-only in previous frozen input directory.
shutil.copytree(T/'frozen/vendor',F/'vendor',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
cfg=json.loads((P.parent/'25_参数0基线/完整母配置.json').read_text(encoding='utf-8'))
(F/'initial.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
settings=json.loads((T/'settings.json').read_text(encoding='utf-8'));settings.update(steps=50000,seed=202609121600,second_seed=202609121601,launch_memory_gb=6,max_parallel=4)
(P/'settings.json').write_text(json.dumps(settings,ensure_ascii=False,indent=2),encoding='utf-8')
cards=[]
for group in range(1,17):
 for ki,kind in enumerate(['projection','small','large','random']):
  for rep in range(1,5):cards.append({'id':f'g{group:02d}_{kind}_{rep:02d}','group':group,'kind':kind,'seed':settings['seed']+group*100+ki*10+rep})
(P/'cards.json').write_text(json.dumps(cards,ensure_ascii=False,indent=2),encoding='utf-8')
common=(T/'common.py').read_text(encoding='utf-8')
common=common.replace("excluded={r['汉字'] for r in read(F/'round1/固定一万句.json')};charset=", "excluded={r['汉字'] for r in read(F/'round1/固定一万句.json')} | {r['汉字'] for r in read(ROOT.parent/'15_自动晋级赛/frozen/round2/固定一万句.json')};charset=")
common=common.replace("fn(F/'raw'/name,200000)","fn(ROOT.parent/'15_自动晋级赛/frozen/raw'/name,200000)")
assert common!=(T/'common.py').read_text(encoding='utf-8')
(P/'common.py').write_text(common,encoding='utf-8')
worker=(T/'worker.py').read_text(encoding='utf-8')
block=" for tier in cfg['optimization']['objective']['characters_short']['tiers']:\n  for level in tier.get('levels',[]):\n   if level['length']==3:level['frequency']*=1.25\n"
assert block in worker;worker=worker.replace(block,'')
worker=worker.replace(" cfg['optimization']['metaheuristic']['parameters']['steps']=SET['steps']", " assert cfg['optimization']==read(F/'initial.json')['optimization'], '参数0不得二次加权'\n cfg['optimization']['metaheuristic']['parameters']['steps']=SET['steps']")
(P/'worker.py').write_text(worker,encoding='utf-8')
controller=(T/'controller.py').read_text(encoding='utf-8').replace('统一2万步','参数0、统一5万步')
needle="   for r in ranked:\n    if r['layout_hash'] not in seen:"
replacement="   for r in ranked:\n    native=read(ROOT/'jobs'/r['id']/'optimized.json')['native']\n    if next(t for t in native['characters_full']['tiers'] if t['top']==300)['effective_duplication']!=0:continue\n    if r['layout_hash'] not in seen:"
assert needle in controller;controller=controller.replace(needle,replacement)
# Preserve ranking evidence and make the exclusion reason machine-readable.
controller=controller.replace("   if len(chosen)<SET['promote']:","   write(ROOT/f'group_{group:02d}_selection.json',{'ranked':[r['id'] for r in ranked],'selected':[r['id'] for r in chosen],'rule':'前300有效重码为0，综合分降序、全赛去重；不足4名停止，不放宽门槛'})\n   if len(chosen)<SET['promote']:")
# Include ordinary tables as part of the automatic final artifact delivery.
needle="  sc=r['score'];pages.append"
replacement="  plain=[]\n  for line in (benchdir/'纯单字码表.txt').read_text(encoding='utf-8').splitlines():\n   code,tail=line.split('=',1);rank,ch=tail.split(',',1);assert len(ch)==1;plain.append(ch+'\\t'+code+'\\n')\n  assert len({line.split('\\t')[0] for line in plain})==8105\n  (folder/'普通纯单字表.txt').write_text(''.join(plain),encoding='utf-8')\n  sc=r['score'];pages.append"
assert needle in controller;controller=controller.replace(needle,replacement)
(P/'controller.py').write_text(controller,encoding='utf-8')
shutil.copy2(T/'keep_awake.py',P/'keep_awake.py')
for n in ['common.py','worker.py','controller.py','keep_awake.py']:py_compile.compile(str(P/n),doraise=True)
files=[f for f in F.rglob('*') if f.is_file() and '__pycache__' not in str(f)]+[P/n for n in ['common.py','worker.py','controller.py','settings.json','cards.json']]
seal={str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
(P/'sealed_inputs.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'运行说明.md').write_text('# 参数0正式晋级赛\n\n256次，每次50000步；16组，每组投影、小改、大改、随机各4个。每组4名进入64强，换语料复测后取5名。参数0、最终评分、字频、根集与简码规则冻结。保留前300有效选重为0晋级门槛，缺额不静默放宽。\n\n第一轮沿用原第一批10000句。第二轮新种子抽样10000句，排除原第一轮和原第二轮全部文本，各来源2500句；所有64方案使用相同新语料。新旧第二轮综合分不能不加说明直接横比。原生退火随机流未固定，种子仅控制初始布局及抽样。\n\n小文件及工具在frozen冻结，原始大语料只读引用E盘原15目录，不重复占用磁盘。四并发上限、内存启动阈值6GB、磁盘12GB、异常自动降并发与重试；进度保存status.json。生成普通单字表和完整双模式结果，不修改正式发布。\n',encoding='utf-8')
print('prepared',len(cards),'cards;',len(seal),'sealed files')
