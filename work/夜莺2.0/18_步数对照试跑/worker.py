from pathlib import Path
import sys,json,copy,traceback,psutil
P=Path(__file__).resolve().parent;T=P.parent/'15_自动晋级赛';sys.path.insert(0,str(T))
from common import *
source=(T/'worker.py').read_text(encoding='utf-8').split('def work(')[0]
start=source.index(" cfg=read(F/'initial.json')");end=source.index(" cfg['optimization']['metaheuristic']['parameters']['steps']",start)
source=source[:start]+" cfg=read(Path(card['original_config']));groups=sorted(k for k in cfg['form']['mapping'] if k.startswith('G'))\n"+source[end:]
ns={'__file__':str(P/'worker.py')};exec(source,ns)
if __name__=='__main__':
 card=next(c for c in read(P/'cards.json') if c['id']==sys.argv[1]);where=P/'jobs'/card['id'];where.mkdir(parents=True,exist_ok=True)
 try:
  psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
  ns['SET']=copy.deepcopy(SET);ns['SET']['steps']=card['steps'];ns['ROOT']=P
  opt=ns['optimize'](card,where)
  actual=read(where/'search/run.json');expected=read(card['original_config']);expected['optimization']['metaheuristic']['parameters']['steps']=card['steps'];assert actual==expected,'除步数外配置发生变化'
  theory=theory_data(opt['native'],opt['code']);write(where/'theory.json',theory)
  bench=bench_module(2,P/'practice',False)['run'](Path(opt['code']),card['id']);score=combine(theory,bench)
  result={'id':card['id'],'baseline':card['baseline'],'label':card['label'],'steps':card['steps'],'score':score,'theory':theory,'benchmark_path':str(P/'practice/results'/card['id']/'结果.json'),'native_score':opt['native_score'],'efficiency':opt['efficiency']}
  write(where/'round2.json',result)
 except Exception:
  (where/'error.txt').write_text(traceback.format_exc(),encoding='utf-8');raise
