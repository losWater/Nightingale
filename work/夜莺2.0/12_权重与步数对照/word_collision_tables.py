from pathlib import Path
from collections import defaultdict
import json,yaml,html
O=Path(__file__).resolve().parent
A=O.parent/'11_多起点试跑'
m=json.loads((O/'manifest.json').read_text(encoding='utf-8'))
e=yaml.safe_load((A/'elements.yaml').read_text(encoding='utf-8'))
words=[json.loads(l) for l in (O.parent/'09_字词避重选词实验/常用加补位词集.jsonl').read_text(encoding='utf-8').splitlines()]
words.sort(key=lambda w:(-w['排序指数'],w['词']))
assert len(words)==60000 and len({w['词'] for w in words})==60000
wb=[2000,5000,10000,20000,50000,60000]
cb=[500,1500,3000,6000,8454]
wl=['1–2000','2001–5000','5001–10000','10001–20000','20001–50000','50001–60000']
cl=['1–500','501–1500','1501–3000','3001–6000','6001–8454']
def band(rank,bounds): return next(i for i,n in enumerate(bounds) if rank<=n)
bycode=defaultdict(list)
for rank,w in enumerate(words,1): bycode[w['实验码']].append((rank,w))
results=[]
for r in sorted(m['results'],key=lambda r:r['id']):
 codes=[l.split('\t') for l in (Path(r['output'])/'code.txt').read_text(encoding='utf-8').splitlines()]
 assert len(codes)==len(e)
 matrices={name:[[0]*6 for _ in cb] for name in ['全部单字全码','剔除有简码字音项']}
 pairs=[]; matched=0; practical=0; rank=0
 for item,c in zip(e,codes):
  assert item['词']==c[0]
  if len(item['词'])!=1: continue
  rank+=1
  short=len(c[3])<4
  hits=bycode.get(c[1],[])
  if hits: matched+=1;practical+=not short
  for wr,w in hits:
   ci,wi=band(rank,cb),band(wr,wb)
   matrices['全部单字全码'][ci][wi]+=1
   if not short: matrices['剔除有简码字音项'][ci][wi]+=1
   pairs.append({'字':c[0],'拼音':item.get('拼音'),'字音排名':rank,'单字全码':c[1],'最短码':c[3],'有简码':short,'词':w['词'],'词频档排名':wr})
 assert rank==8454
 totals={k:sum(map(sum,v)) for k,v in matrices.items()}
 assert totals['剔除有简码字音项']<=totals['全部单字全码']==len(pairs)
 red={k:sum(sum(row[:3]) for row in v[:2]) for k,v in matrices.items()}
 results.append({'组别':r['id'],'矩阵':matrices,'冲突对合计':totals,'前1500字音×前10000词':red,'碰撞字音项':matched,'剔除有简后碰撞字音项':practical})
 (O/(r['id']+'_字词碰撞明细.json')).write_text(json.dumps(pairs,ensure_ascii=False,indent=2),encoding='utf-8')
intro='统计单字四码与词语四码相同的字音—词对；一个字遇到多个同码词分别计对。左表保留全部单字全码，右表剔除拥有一、二、三简的字音项。简词不参与，补三简不重复计数。字频按本轮8454字音项排序（8105个字），不是去重汉字排名；词频按本轮选出的60000词的排序指数降序排列，不代表原始语料绝对频次。各档互不重叠，末列是50001–60000，不是库外。'
lines=['# 字词碰撞分档对照','',intro,'','常用区：前1500字音项 × 前10000词。表格数字为冲突对数，不是冲突字数。','']
for r in results:
 lines+=['## '+r['组别'],'']
 for name,mat in r['矩阵'].items():
  lines+=['### '+name,'',f"冲突对合计：{r['冲突对合计'][name]}；常用区：{r['前1500字音×前10000词'][name]}。",'','|字音频档 / 词频档|'+'|'.join(wl)+'|合计|','|---|'+'---:|'*7]
  for label,row in zip(cl,mat):lines.append('|'+label+'|'+'|'.join(map(str,row))+'|'+str(sum(row))+'|')
  lines+=['']
(O/'字词碰撞分档对照.md').write_text('\n'.join(lines),encoding='utf-8')
(O/'字词碰撞分档汇总.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
parts=['<!doctype html><meta charset="utf-8"><title>字词碰撞分档对照</title><style>body{font-family:system-ui;background:#f4f7fb;color:#213448;margin:32px}section{display:flex;gap:20px;flex-wrap:wrap}article{background:white;padding:18px;border-radius:12px;overflow:auto}table{border-collapse:collapse}th,td{padding:10px;border:1px solid #ccd9e5;text-align:right}th{background:#e3edf5}h2{margin-top:36px}.red{outline:2px solid #bd5145;outline-offset:-2px}p{max-width:1100px;line-height:1.7}</style><h1>字词碰撞分档对照</h1><p>'+html.escape(intro)+'</p><p>红框单元格：前1500字音项 × 前10000词。</p>']
for r in results:
 parts+=['<h2>'+r['组别']+'</h2><section>']
 for name,mat in r['矩阵'].items():
  parts+=['<article><h3>'+name+'</h3><p>冲突对 '+str(r['冲突对合计'][name])+' · 常用区 '+str(r['前1500字音×前10000词'][name])+'</p><table><tr><th>字音 / 词频档</th>'+''.join('<th>'+w+'</th>' for w in wl)+'<th>合计</th></tr>']
  for i,(label,row) in enumerate(zip(cl,mat)):
   parts+=['<tr><th>'+label+'</th>'+''.join('<td'+(' class="red"' if i<2 and j<3 else '')+'>'+str(n)+'</td>' for j,n in enumerate(row))+'<td>'+str(sum(row))+'</td></tr>']
  parts+=['</table></article>']
 parts+=['</section>']
(O/'字词碰撞分档对照.html').write_text(''.join(parts),encoding='utf-8')
print(json.dumps([{k:v for k,v in r.items() if k!='矩阵'} for r in results],ensure_ascii=False))
