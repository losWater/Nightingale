from common import *
import subprocess,traceback,psutil,argparse

from search_worker import optimize

def work(card,roundno,details=False):
 where=ROOT/'jobs'/card['id'];where.mkdir(parents=True,exist_ok=True)
 if roundno==1:
  optimized=optimize(card,where);theory=theory_data(optimized['native'],optimized['code']);write(where/'theory.json',theory)
 else:optimized=read(where/'optimized.json');theory=read(where/'theory.json')
 ns=bench_module(roundno,ROOT/f'round{roundno}',details);bench=ns['run'](Path(optimized['code']),card['id']);score=combine(theory,bench)
 result={'id':card['id'],'group':card['group'],'kind':card['kind'],'round':roundno,'score':score,'layout_hash':optimized['layout_hash'],'theory':theory,'benchmark_path':str(ROOT/f'round{roundno}'/'results'/card['id']/'结果.json')}
 write(where/f'round{roundno}.json',result)
 return result
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('id');ap.add_argument('--round',type=int,default=1);ap.add_argument('--details',action='store_true');args=ap.parse_args()
 try:
  psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
  card=next(c for c in read(ROOT/'cards.json') if c['id']==args.id);work(card,args.round,args.details)
 except Exception:
  (ROOT/'jobs'/args.id).mkdir(parents=True,exist_ok=True)
  (ROOT/'jobs'/args.id/f'error_round{args.round}.txt').write_text(traceback.format_exc(),encoding='utf-8');raise
