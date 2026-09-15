from pathlib import Path
import sys,json,statistics,html
P=Path(__file__).resolve().parent;T=P.parent/'15_自动晋级赛';sys.path.insert(0,str(T))
from common import read,write,bench_module,yload
F=T/'frozen';es=[e for e in yload(F/'elements.yaml') if len(e['词'])==1]
ns=bench_module(2,P/'分档临时',False);EQ=ns['EQ'];ends=[300,500,1500,3000,6000,8454]
labels=['1–300','301–500','501–1500','1501–3000','3001–6000','6001–8454']
rank={}
for i,e in enumerate(es):rank.setdefault((e['词'],''.join(x['element'][2:] for x in e['元素序列'][:2])),i)
assert len(rank)==8452
corpus=read(F/'round2/固定一万句.json');base=read(F/'round2/字音基准.json');results=[]
for id in read(P/'参数集稳定性.json')['完整统计']['0']['样本']:
 o=read(P/'jobs'/id/'optimized.json');d=read(P/'jobs'/id/'round2.json');pure,options,_=ns['load_chars'](Path(o['code']))
 seq={}
 for key,opts in options.items():
  code,pos=min(((c,pure[c].index(key[0])+1) for c in opts),key=lambda x:(len(x[0]),x[1],x[0]));seq[key]=code+ns['commit'](pos)
 def binof(key):return next(j for j,end in enumerate(ends) if rank[key]<end)
 def add(acc,key,s,w):
  j=binof(key)
  for a,b in zip(s,s[1:]):acc[j][0]+=EQ[a+b]*w;acc[j][1]+=w
 theory=[[0.,0] for _ in labels];practice=[[0.,0] for _ in labels]
 for e in base:
  key=(e['字'],e['音码']);add(theory,key,seq[key],e['频率'])
 for row in corpus:
  prev=''
  for ch,pr in zip(row['汉字'],row['音码']):
   key=(ch,pr);s=seq[key];add(practice,key,prev+s,1);prev=s[-1]
 for name,acc,expected in [('理论',theory,d['benchmark']['理论当量_统一46键表']['键均当量']),('实战',practice,d['benchmark']['实战']['纯单字']['键均当量'])]:
  whole=sum(x[0] for x in acc)/sum(x[1] for x in acc);assert abs(whole-expected)<1e-9,(id,name,whole,expected)
 results.append({'id':id,'理论':[a/b if b else None for a,b in theory],'实战':[a/b if b else None for a,b in practice],'理论分子分母':theory,'实战分子分母':practice})
rows=[]
for j,label in enumerate(labels):
 r={'字频档':label}
 for name in ['实战','理论']:
  vals=[x[name][j] for x in results if x[name][j] is not None]
  r[name+'均值']=statistics.mean(vals) if vals else None;r[name+'最低']=min(vals) if vals else None;r[name+'最高']=max(vals) if vals else None
 rows.append(r)
write(P/'参数0分档键均当量.json',{'口径':'既定8454字音频次排序；实战按键对后一键所属字归档，包含跨字转换但不跨句；理论各字独立输入、含提交键、字音频次加权。各档先计算当量总和/键对数，再对8次运行取算术平均。末档理论无分配频次，留空。','汇总':rows,'明细':results})
ks=list(rows[0]);table='<table><tr>'+''.join('<th>'+k+'</th>' for k in ks)+'</tr>'+''.join('<tr>'+''.join('<td>'+('—' if r[k] is None else f'{r[k]:.5f}' if isinstance(r[k],float) else r[k])+'</td>' for k in ks)+'</tr>' for r in rows)+'</table>'
(P/'参数0分档键均当量.html').write_text('<!doctype html><meta charset="utf-8"><title>参数0分档键均当量</title><style>body{font:16px system-ui;margin:32px;background:#f3f6fa}td,th{padding:12px;border:1px solid #ccc}table{border-collapse:collapse}p{max-width:1000px;line-height:1.8}</style><h1>参数0：8次运行的分档键均当量</h1><p>实战为同一万句纯单字输入；跨字转换键对归入后一字，不跨句。理论为各字独立输入并按字音频次加权，均含提交键，使用同一46键当量表。范围按既定8454字音项排序，不是8105字去重排名。同字同音码重复项（哼、咯）按最前排名归档，实战数据不能区分同音码读法。低值更好；末档理论无已分配频次，不记作零。分档分子分母汇总已核对每次原报告总体值，误差小于1e-9。</p>'+table,encoding='utf-8')
print(json.dumps(rows,ensure_ascii=False))
