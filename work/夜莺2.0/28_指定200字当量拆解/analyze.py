from pathlib import Path
from collections import defaultdict,Counter
import json,html,shutil,hashlib
P=Path(__file__).resolve().parent;W=P.parent;F=W/'27_删利根参数0晋级赛/frozen';V=W/'16_1.0同口径复测'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
source=Path(r'D:\nightingale\releases\v0.9.1\99_参考资料\参考\300-500.txt');shutil.copyfile(source,P/'用户200字名单.txt');chs=source.read_text(encoding='utf-8-sig').split();assert len(chs)==len(set(chs))==200
base=read(F/'字音基准.json');raw=[l.split('\t') for l in (V/'1.0字音最短码明细.txt').read_text(encoding='utf-8').splitlines()[1:]];assert len(raw)==len(base)
eq={}
for l in (F/'当量表.tsv').read_text(encoding='utf-8').splitlines():
 if '\t' in l:
  k,v=l.split('\t')
  if len(k)==2:eq[k]=float(v)
labels=['音码内部','音形衔接','形码内部','提交及翻页','特殊入口内部']
rows=[];by=defaultdict(list)
for b,r in zip(base,raw):
 rank,ch,py,code,pos=r;pos=int(pos);assert ch==b['字'] and py==b['拼音'];commit='='*((pos-1)//3)+[' ',';',"'"][(pos-1)%3];seq=code+commit;parts=[];costs={k:0. for k in labels}
 for i in range(len(seq)-1):
  pair=seq[i:i+2]
  if i>=len(code)-1:cat='提交及翻页'
  elif not code.startswith(b['音码']):cat='特殊入口内部'
  elif i==0:cat='音码内部'
  elif i==1:cat='音形衔接'
  else:cat='形码内部'
  value=eq[pair];costs[cat]+=value;parts.append({'键对':pair,'环节':cat,'当量':value})
 row={'字':ch,'拼音':py,'现字音排名':int(rank),'频率':b['频率'],'音码':b['音码'],'最短码':code,'候选位':pos,'输入序列':seq,'键对数':len(seq)-1,'总当量':sum(costs.values()),'键均当量':sum(costs.values())/(len(seq)-1),'成本':costs,'键对':parts,'音码固定键对当量':eq[b['音码']]};rows.append(row);by[ch].append(row)
selected=[by[ch][0].copy() for ch in chs]
for i,r in enumerate(selected,301):r['用户名单序号']=i
allreadings=[r for r in rows if r['字'] in chs]
def summary(items,weighted):
 den=sum(r['键对数']*(r['频率'] if weighted else 1) for r in items);cost=sum(r['总当量']*(r['频率'] if weighted else 1) for r in items)
 return {'字音项':len(items),'键均当量':cost/den,'平均音码固定键对':sum(r['音码固定键对当量']*(r['频率'] if weighted else 1) for r in items)/sum(r['频率'] if weighted else 1 for r in items),'码长分布':dict(Counter(len(r['最短码']) for r in items)),'分环节贡献':{k:sum(r['成本'][k]*(r['频率'] if weighted else 1) for r in items)/den for k in labels},'分母':den}
summaries={}
for title,items in [('用户200字主读',selected),('用户200字全部读音',allreadings),('当前字频1–300字音项',rows[:300]),('当前字频301–500字音项',rows[300:500]),('当前字频501–1500字音项',rows[500:1500])]:
 for weight in [False,True]:summaries[title+('·频次加权' if weight else '·等权')]=summary(items,weight)
ref=summaries['用户200字主读·频次加权']['键均当量'];den=summaries['用户200字主读·频次加权']['分母']
for r in selected:
 r['高于本组均值的加权贡献']=(r['总当量']-ref*r['键对数'])*r['频率']/den
 r['音码成本占比']=r['成本']['音码内部']/r['总当量']
pairs=defaultdict(lambda:{'加权成本':0.,'等权出现字数':0,'字':[]})
for r in selected:
 for part in r['键对']:
  key=part['环节']+' '+part['键对'];d=pairs[key];d['加权成本']+=part['当量']*r['频率'];d['等权出现字数']+=1;d['字'].append(r['字'])
write(P/'逐字当量拆解.json',{'口径':'冻结夜莺1.0实际简码与候选顺序；每字独立输入，所有码长均有提交键，键均当量=键对成本和/键对数；不含跨字转换。200字主读是当前审计字频最高的读音，另列全部读音。不能直接复现缺少原字频与上屏设置的外部测评。','汇总':summaries,'主读200字':selected,'全部读音':allreadings,'键对成本':dict(pairs),'当前301–500重合字数':len(set(chs)&{r['字'] for r in rows[300:500]})})
# Validate against the existing full-corpus theoretical total, so formulas and entry selection agree.
expected=read(V/'results/夜莺1.0/结果.json')['理论当量_统一46键表']['键均当量'];actual=summary(rows,True)['键均当量'];assert abs(actual-expected)<1e-9,(actual,expected)
inputs=[source,V/'1.0字音最短码明细.txt',F/'字音基准.json',F/'当量表.tsv',V/'1.0原表快照.txt'];write(P/'核验.json',{'200字无重复且全部覆盖':True,'总体理论当量复算':actual,'原报告':expected,'误差':actual-expected,'输入指纹':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs}})
def fmt(v):return f'{v:.4f}' if isinstance(v,float) else str(v)
def table(headers,data):return '<table><thead><tr>'+''.join('<th>'+html.escape(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+html.escape(fmt(v))+'</td>' for v in row)+'</tr>' for row in data)+'</tbody></table>'
def visible(s):return s.replace(' ','␣')
ranked=sorted(selected,key=lambda r:-r['高于本组均值的加权贡献'])
page='<!doctype html><meta charset="utf-8"><title>200字逐字当量拆解</title><style>body{font:16px/1.6 system-ui;margin:30px;background:#f5f7fb;color:#234}table{border-collapse:collapse;background:white;margin:20px 0}th,td{border:1px solid #ccd5df;padding:8px}th{position:sticky;top:0;background:#e1ebf3}input{font:inherit;padding:8px}p{max-width:1200px}.wrap{overflow:auto}</style><h1>夜莺1.0：指定200字当量拆解</h1><p>使用用户名单，当前主读每字一条。与现字频301–500位仅重合68字，不把两档混算。简码保留1.0原表实际分配。␣代表空格；含提交键，不含跨字转换。加权使用现有审计分读音字频，不能直接复现外部旧字频测评。</p><p>各环节“贡献”相加等于键均当量；它不是该环节自身键对的平均值。一、二简没有音形衔接成本；非音码前缀入口另列，避免误归因。这里没有修改任何根、简码或退火参数。</p>'
page+='<h2>不同字集与权重口径</h2><div class="wrap">'+table(['范围','项数','键均当量','固定两位音码均值','音内部贡献','音形贡献','形内部贡献','提交贡献','特殊入口贡献'],[[k,v['字音项'],v['键均当量'],v['平均音码固定键对'],*[v['分环节贡献'][l] for l in labels]] for k,v in summaries.items()])+'</div>'
page+='<h2>最值得先检查的20字</h2><p>按“高于本组均值的加权贡献”排序：兼顾出现频率、码长和实际成本，不等同于改键后的可实现收益。</p>'+table(['字','拼音','现排名','输入','键均当量','超均值贡献','逐键对成本'],[[r['字'],r['拼音'],r['现字音排名'],visible(r['输入序列']),r['键均当量'],r['高于本组均值的加权贡献'],'；'.join(visible(x['键对'])+'='+str(x['当量'])+'（'+x['环节']+'）' for x in r['键对'])] for r in ranked[:20]])
page+='<h2>全部200字</h2><input id="q" placeholder="搜索字、拼音或编码"><div id="all">'+table(['名单序号','字','拼音','现字音排名','频率','最短码','位','键均当量','音内部','音形衔接','形内部','提交','特殊入口','逐键对'],[[r['用户名单序号'],r['字'],r['拼音'],r['现字音排名'],r['频率'],r['最短码'],r['候选位'],r['键均当量'],*[r['成本'][k] for k in labels],' / '.join(visible(t['键对'])+' '+str(t['当量']) for t in r['键对'])] for r in selected])+'</div><script>document.getElementById("q").oninput=function(){document.querySelectorAll("#all tbody tr").forEach(r=>r.hidden=!r.textContent.includes(this.value.trim()))}</script>'
(P/'逐字当量拆解.html').write_text(page,encoding='utf-8')
md='# 指定200字当量拆解\n\n夜莺1.0原表，现审计字频，独立单字含提交键。名单与现301–500仅重合68字。\n\n|字|读音|输入|键均当量|音内部|音形衔接|形内部|提交|逐键对|\n|---|---|---|---:|---:|---:|---:|---:|---|\n'
for r in selected:md+='|'+ '|'.join(map(str,[r['字'],r['拼音'],visible(r['输入序列']),round(r['键均当量'],4),*[r['成本'][k] for k in labels[:4]],' / '.join(visible(t['键对'])+'='+str(t['当量']) for t in r['键对'])]))+'|\n'
(P/'逐字当量拆解.md').write_text(md,encoding='utf-8')
print(json.dumps({'汇总':summaries,'优先检查':[{k:r[k] for k in ['字','拼音','最短码','键均当量','键对']} for r in ranked[:12]],'高音码':[{'字':r['字'],'音码':r['音码'],'成本':r['音码固定键对当量']} for r in sorted(selected,key=lambda r:-r['音码固定键对当量'])[:15]]},ensure_ascii=False))
