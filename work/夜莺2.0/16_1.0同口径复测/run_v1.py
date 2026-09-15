from pathlib import Path
from collections import defaultdict,Counter
import json,sys,shutil,html
P=Path(__file__).resolve().parent;T=P.parent/'15_自动晋级赛';sys.path.insert(0,str(T))
from common import bench_module,read,write,sha
source=Path('E:/夜莺2.0/releases/v1.0/01_正式码表/夜莺码v1.0单字版.txt')
shutil.copyfile(source,P/'1.0原表快照.txt')
base=read(T/'frozen/字音基准.json');by=defaultdict(list)
for b in base:by[b['字']].append(b['音码'])
rows=[l.split() for l in source.read_text(encoding='utf-8-sig').splitlines()];assert all(len(r)==2 for r in rows)
core=[(ch,c) for ch,c in rows if ch in by];assert len({ch for ch,c in core})==8105
corefile=P/'夜莺1.0_8105纯单字.txt';corefile.write_text(''.join(ch+'\t'+c+'\n' for ch,c in core),encoding='utf-8')
audit=[]
def load(path):
 tables=defaultdict(list);options=defaultdict(set)
 for ch,code in core:
  assert code.isascii() and code.isalpha() and 1<=len(code)<=4
  if ch not in tables[code]:tables[code].append(ch)
  if len(code)==1:pr=by[ch][0]
  elif code[:2] in by[ch]:pr=code[:2]
  else:
   pr=by[ch][0];audit.append({'字':ch,'码':code,'归属音码':pr,'说明':'非该字已知音码前缀，按主读容错入口处理'})
  options[ch,pr].add(code)
 short=set()
 for (ch,pr),codes in options.items():
  if any(len(c)<4 for c in codes):
   short.add((ch,pr))
   for c in codes:
    if len(c)==4:short.add((ch,c[:2]))
 assert all(options[b['字'],b['音码']] for b in base)
 return dict(tables),options,short
ns=bench_module(2,P,False);ns['load_chars']=load
result=ns['run'](corefile,'夜莺1.0');write(P/'入口读音映射说明.json',audit)
pure,options,_=load(corefile);bins=[];readable=['序\t字\t读音\t最短码\t位']
chosen=[]
for i,b in enumerate(base,1):
 codes=options[b['字'],b['音码']];code=min(codes,key=lambda c:(len(c),pure[c].index(b['字']),c));pos=pure[code].index(b['字'])+1
 chosen.append((b,code,pos));readable.append(f'{i}\t{b["字"]}\t{b["拼音"]}\t{code}\t{pos}')
for lo,hi in zip([0,300,500,1500,3000,6000],[300,500,1500,3000,6000,8454]):
 seg=chosen[lo:hi];counts=Counter(len(c) for b,c,pos in seg);short=[(b,c,pos) for b,c,pos in seg if len(c)<=3 and pos==1];den=sum(b['频率'] for b,c,pos in seg)
 bins.append({'区间':f'{lo+1}–{hi}','一简':counts[1],'二简':counts[2],'三简':counts[3],'四码':counts[4],'≤三码首选':len(short),'字频覆盖':sum(b['频率'] for b,c,pos in short)/den if den else None})
coverage=sum(b['频率'] for b,c,pos in chosen if len(c)<=3 and pos==1)/sum(b['频率'] for b,c,pos in chosen)
(P/'1.0字音最短码明细.txt').write_text('\n'.join(readable),encoding='utf-8')
write(P/'1.0理论分段.json',{'分段':bins,'总覆盖':coverage,'首选项数':sum(b['≤三码首选'] for b in bins)})
finals=read(T/'最终五名.json');benchmarks=[result]+[read(Path(r['benchmark_path'])) for r in finals];labels=['1.0','A','B','C','D','E']
for b in benchmarks:
 for mode,v in b['实战'].items():
  assert v['可计分'] and v['目标字次']==147687
 assert b['固定输入']['sha256']==result['固定输入']['sha256']
# 计分使用冻结草案3实战公式；不反推1.0的原生理论优化分。
def practice(d):
 def s(x,b,a):return b/(1+x/a)
 return sum([s(abs(d['左手占比_不含空格']-.5),10,.05),s(d['小指占比_不含空格'],10,.2),s(d['最高单键占比_不含空格'],10,.1),s(d['最高单指占比_不含空格'],10,.25),s(d['键均当量'],10,1.3),s(d['字均当量'],20,4),s(max(0,d['每字击键']-1),20,2),s(d['字字选重率_单字上屏'],5,.02),s(d['字词增量受影响率'],5,.02)])
for r,b in zip(finals,benchmarks[1:]):
 for mode,d in b['实战'].items():assert abs(practice(d)-r['score']['practice'][mode]['score'])<1e-9
summary={'理论分段':bins,'理论覆盖':coverage,'实战':{m:practice(d) for m,d in result['实战'].items()},'源SHA256':sha(source),'核心导出SHA256':sha(corefile),'说明':'同字集、字音频率、语料、词库、上屏规则；1.0保留原表容错入口和简码，不新增补三简。1.0综合分未计算，未将不兼容的原生理论指标拼接成总分。'}
write(P/'复测汇总.json',summary)
md=['# 夜莺1.0与五个候选同口径复测','','同一核心字集8105字；理论按8454字音项，实战为同一第二轮10000句147687字次、固定60000四码词。1.0从E盘冻结历史原表读取，保留原简码、容错入口与同码相对顺序；只移除字集之外的字，不改原文件。单字一简按主读音归属，不跨读音借简码。非已知音码前缀的容错入口按主读处理，明细已保存。','', '比较统一的纯单字和固定词库混排表现，不等同于1.0原发布词库或某款输入法自动上屏的实测。所有组实际键数含上屏键。词词冲突单列、不直接扣冲突分，实际成本仍进入按键、当量和热力。上下文工具读音仍有误判可能。','', '1.0保留原有容错码，2.0候选使用当前导出入口；这是现有可用码表的比较，不单独归因于根布局。1.0原生理论优化指标未在本轮重新构造，因此本报告不提供1.0的理论综合分或总分。']
ht=['<!doctype html><meta charset="utf-8"><title>1.0同口径复测</title><style>body{font:16px system-ui;background:#f4f7fb;color:#234;margin:28px}p{max-width:1250px;line-height:1.8}table{border-collapse:collapse;background:white;margin:18px 0}th,td{padding:9px;border:1px solid #bdd0de;text-align:right}th{background:#dceaf5}.wrap{overflow:auto}</style><h1>夜莺1.0与五个候选同口径复测</h1>']
ht+=['<p>'+html.escape(x)+'</p>' for x in md[2:] if x]
def fmt(x):return '未分配' if x is None else f'{x:.4f}'
def pct(x):return '未分配' if x is None else f'{x:.3%}'
def table(title,rows):
 md.extend(['','## '+title,'','|指标|'+'|'.join(labels)+'|','|---|'+'---:|'*6]);ht.append('<h2>'+title+'</h2><div class="wrap"><table><tr><th>指标</th>'+''.join('<th>'+x+'</th>' for x in labels)+'</tr>')
 for row in rows:md.append('|'+'|'.join(map(str,row))+'|');ht.append('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>')
 ht.append('</table></div>')
table('理论≤三码首选数量',[[b['区间'],b['≤三码首选']]+[r['theory']['分段'][i]['≤三码首选'] for r in finals] for i,b in enumerate(bins)])
table('理论≤三码段内字频覆盖',[[b['区间'],pct(b['字频覆盖'])]+[pct(r['theory']['分段'][i]['字频覆盖']) for r in finals] for i,b in enumerate(bins)])
table('理论整体', [['≤三码首选总量',sum(b['≤三码首选'] for b in bins)]+[sum(b['≤三码首选'] for b in r['theory']['分段']) for r in finals],['字频覆盖',pct(coverage)]+[pct(read(T/'jobs'/r['id']/'optimized.json')['efficiency']['三码及以内首选字频覆盖']) for r in finals],*[[k]+[fmt(b['理论当量_统一46键表'][k]) for b in benchmarks] for k in ['键均当量','字均当量']]])
for mode in ['纯单字','无简词字词']:
 rows=[['实战分 ↑']+[fmt(practice(b['实战'][mode])) for b in benchmarks]]
 for k in ['每字击键','键均当量','字均当量','选重率_每次上屏','字字选重率_单字上屏','字词增量受影响率','大跨排率','小跨排率','左手占比_不含空格','小指占比_不含空格','最高单键占比_不含空格','字占位导致拆词次数']:
  form=pct if ('率' in k or '占比' in k) else fmt
  rows.append([k]+[form(b['实战'][mode].get(k,0)) for b in benchmarks])
 table(mode+'实战',rows)
(P/'1.0与五个候选对照.md').write_text('\n'.join(md),encoding='utf-8');(P/'1.0与五个候选对照.html').write_text(''.join(ht),encoding='utf-8')
print(json.dumps({'core_lines':len(core),'aliases':len(audit),'theory':summary,'results':{m:{k:d[k] for k in ['每字击键','键均当量','字均当量','字字选重率_单字上屏','字词增量受影响率']} for m,d in result['实战'].items()}},ensure_ascii=False))
