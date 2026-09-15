from pathlib import Path
import json,yaml,subprocess,psutil,hashlib,html
P=Path(__file__).resolve().parent;W=P.parent;F=W/'27_删利根参数0晋级赛/frozen';O=W/'33_新字频固定布局试验';O.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
base=read(F/'字音基准.json');new=read(P/'分音字频_试验.json');scale=sum(x['频率'] for x in base)/1e6
oldfreq={(x['字'],x['拼音']):x['频率'] for x in base};newfreq={(x['字'],x['拼音']):x['优化权重']*scale for x in new}
# The same historical optimization override is applied to both arms.
total=sum(x['频率'] for x in base if x['字']=='谁')
for k in oldfreq:
 if k[0]=='谁':oldfreq[k]=0 if k[1]=='shei' else total/4
cfg=read(F/'initial.json');elements=yaml.safe_load((F/'elements.yaml').read_text(encoding='utf-8'));summary={}
for tag,freq in [('旧频_同规则',oldfreq),('新频_估计分音',newfreq)]:
 d=O/tag;d.mkdir(exist_ok=True);el=json.loads(json.dumps(elements,ensure_ascii=False));changed=0
 for e in el:
  k=(e['词'],e.get('拼音'))
  if k in freq:e['频率']=round(freq[k]);changed+=1
 assert changed==len(base),(changed,len(base))
 el=sorted([e for e in el if (e['词'],e.get('拼音')) in freq],key=lambda e:(-e['频率'],e['词'],e['拼音']))+[e for e in el if (e['词'],e.get('拼音')) not in freq]
 # Native input weights are integers; preserve the much larger original scale to minimize rounding.
 (d/'elements.yaml').write_text(yaml.safe_dump(el,allow_unicode=True,sort_keys=False),encoding='utf-8');write(d/'run.json',cfg)
 assert psutil.virtual_memory().available>3*2**30,'不足3GiB，停止试验'
 cmd=[str(F/'chai.exe'),'encode',str(d/'run.json'),'-e',str(d/'elements.yaml'),'-k',str(F/'distribution.txt'),'-p',str(F/'equivalence.txt')]
 with (d/'stdout.log').open('w',encoding='utf-8') as o,(d/'stderr.log').open('w',encoding='utf-8') as er:
  child=subprocess.Popen(cmd,cwd=d,stdout=o,stderr=er,creationflags=subprocess.CREATE_NO_WINDOW)
  try:rc=child.wait(timeout=180)
  except subprocess.TimeoutExpired:child.kill();child.wait();raise
 assert rc==0,(tag,rc,(d/'stderr.log').read_text(encoding='utf-8')[-1000:])
 out=sorted(d.glob('output-*/metric.json'))[-1];m=read(out);summary[tag]={'结果目录':str(out.parent),'原生结果':m,'输入变更字音数':changed}
 print(tag,'完成',m['score'],flush=True)
write(O/'结果.json',summary)
write(O/'试验说明.json',{'模式':'encode固定布局，不退火','布局来源':str(F/'initial.json'),'比较说明':'相同删利根集、投影布局、简码锁定与参数；只换频率。各自按频率重新生成简码；两臂评测权重及频序不同，得分不用于判定布局优劣。','新频缩放':scale,'谁规则':'两臂shei优化0、shui取各自整字频率1/4；旧频自然表已缺失谁大量频次，旧频此项只能作受损基线。','输入sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [F/'initial.json',F/'elements.yaml',P/'分音字频_试验.json']}})
page='<!doctype html><meta charset="utf-8"><title>新字频固定布局试验</title><style>body{font:16px/1.7 system-ui;background:#f4f7fb;margin:25px}pre{white-space:pre-wrap;background:white;padding:20px}</style><h1>新旧字频 · 固定布局试验</h1><p>只重算编码和简码，不运行退火。根集、布局、参数固定；两臂各自按频率重新排名，因此得分差异不能直接解释为布局性能提升。</p>'
for tag,v in summary.items():page+='<h2>'+tag+'</h2><pre>'+html.escape(json.dumps(v['原生结果'],ensure_ascii=False,indent=2))+'</pre>'
(O/'固定布局试验.html').write_text(page,encoding='utf-8')
