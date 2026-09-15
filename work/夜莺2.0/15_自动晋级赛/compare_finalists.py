from pathlib import Path
import json,html
P=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
rs=read(P/'最终五名.json'); bs=[read(Path(r['benchmark_path'])) for r in rs]; opts=[read(P/'jobs'/r['id']/'optimized.json') for r in rs]
labels=list('ABCDE');md=['# 五个最终候选性能横向对照','', '本页只整理已完成结果，不重新退火或改变评分。A–E对应最终排名。实战均为第二轮同一10000句、147687字次，固定60000二字四码词，无简词。所有方案缺字音为0、当量表覆盖率100%。','', '理论排名单位为8454个字音项（8105个汉字），不是去重字数。≤三码包含一二三简首选，补三简不重复计数；末档无已分配字频，不当成真实零频。实战显式计算上屏键，无四码自动上屏；工具读音不是逐句人工校准。']
ht=['<!doctype html><meta charset="utf-8"><title>五个最终候选性能横向对照</title><style>body{font-family:system-ui;background:#f4f7fb;color:#213448;margin:28px}h2{margin-top:32px}p{line-height:1.7;max-width:1300px}.wrap{overflow:auto}table{border-collapse:collapse;background:white;margin:16px 0;min-width:900px}th,td{border:1px solid #c3d3e0;padding:10px;text-align:right}th:first-child,td:first-child{text-align:left}th{background:#deebf6;position:sticky;top:0}.matrices{display:flex;gap:16px;flex-wrap:wrap}.matrices table{min-width:700px}a{color:#285f9d}</style><h1>五个最终候选性能横向对照</h1>']
ht+=['<p>'+html.escape(s)+'</p>' for s in md[2:] if s]
def table(title,rows,headers=None):
 headers=headers or ['指标']+labels;md.extend(['','## '+title,'','|'+'|'.join(headers)+'|','|'+'|'.join(['---']+['---:']*(len(headers)-1))+'|'])
 ht.extend(['<h2>'+html.escape(title)+'</h2><div class="wrap"><table><tr>'+''.join('<th>'+html.escape(h)+'</th>' for h in headers)+'</tr>'])
 for row in rows:
  md.append('|'+'|'.join(str(x) for x in row)+'|');ht.append('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>')
 ht.append('</table></div>')
def pct(v,n=3):return '未分配' if v is None else f'{v:.{n}%}'
def num(v):return '未提供' if v is None else f'{v:.4f}'
table('身份与得分',[
 ['方案编号']+[r['id'] for r in rs],['开局']+[{'small':'1.0小改','large':'1.0大改','random':'完全随机'}[r['kind']] for r in rs],
 ['综合分 ↑']+[num(r['score']['total']) for r in rs],['理论分 ↑']+[num(r['score']['theory']) for r in rs],
 *[[m+'实战分 ↑']+[num(r['score']['practice'][m]['score']) for r in rs] for m in ['纯单字','无简词字词']]])
table('理论整体效率',[
 ['一简 / 二简']+[f"{o['efficiency']['最短码长分布']['1']} / {o['efficiency']['最短码长分布']['2']}" for o in opts],
 ['三简项数 ↑']+[o['efficiency']['最短码长分布']['3'] for o in opts],
 ['四码项数 ↓']+[o['efficiency']['最短码长分布']['4'] for o in opts],
 ['≤三码首选数量 ↑']+[o['efficiency']['三码及以内首选项数'] for o in opts],
 ['≤三码首选字频覆盖 ↑']+[pct(o['efficiency']['三码及以内首选字频覆盖']) for o in opts],
 ['理论有效全码选重率 ↓']+[pct(o['native']['characters_full']['effective_duplication']) for o in opts],
 ['理论键均当量 ↓']+[num(b['理论当量_统一46键表']['键均当量']) for b in bs],
 ['理论字均当量 ↓']+[num(b['理论当量_统一46键表']['字均当量']) for b in bs]])
for field,title in [('≤三码首选','理论分段：≤三码首选数量'),('字频覆盖','理论分段：≤三码段内字频覆盖')]:
 rows=[]
 for j,seg in enumerate(rs[0]['theory']['分段']):rows.append([seg['区间']]+[(pct(r['theory']['分段'][j][field]) if field=='字频覆盖' else r['theory']['分段'][j][field]) for r in rs])
 table(title,rows)
table('理论分段：一简 / 二简 / 三简 / 四码',[[seg['区间']]+[' / '.join(str(r['theory']['分段'][j][f]) for f in ['一简','二简','三简','四码']) for r in rs] for j,seg in enumerate(rs[0]['theory']['分段'])])
rows=[]
for layer in ['全部单字全码','剔除有简码字音项']:
 rows.append([layer+'：全范围冲突对 ↓']+[sum(map(sum,r['theory']['字词矩阵'][layer])) for r in rs])
 rows.append([layer+'：前1500字音×前10000词 ↓']+[sum(sum(row[:3]) for row in r['theory']['字词矩阵'][layer][:2]) for r in rs])
table('静态字词碰撞概览',rows)
for mode in ['纯单字','无简词字词']:
 datasets=[b['实战'][mode] for b in bs];rows=[]
 for name,f,fmt in [('每字实际击键 ↓','每字击键',num),('键均当量 ↓','键均当量',num),('字均当量 ↓','字均当量',num),('完整选重率（含词词，仅展示）','选重率_每次上屏',pct),('字字选重率 ↓','字字选重率_单字上屏',pct),('字词增量影响率 ↓','字词增量受影响率',pct),('同指大跨排 ↓','大跨排率',pct),('同指小跨排 ↓','小跨排率',pct),('同键连击率 ↓','同键连击率',pct),('同指异键率 ↓','同指异键率',pct),('同键三连率 ↓','同键三连率',pct),('同键四连率 ↓','同键四连率',pct),('同指三连率 ↓','同指三连率',pct),('同指四连率 ↓','同指四连率',pct),('左手占比（不含空格）','左手占比_不含空格',pct),('小指负担（不含空格）↓','小指占比_不含空格',pct),('最高单键占比（不含空格）↓','最高单键占比_不含空格',pct),('最高单指占比（不含空格）↓','最高单指占比_不含空格',pct)]:rows.append([name]+[fmt(d.get(f)) for d in datasets])
 table(mode+'实战：效率、当量与手感',rows)
 table(mode+'实战：最高负担编码键',[[f'第{i+1}高']+[f'{k}：{pct(v/sum(d["编码键热力"].values()))}' for d in datasets for k,v in [sorted(d['编码键热力'].items(),key=lambda x:(-x[1],x[0]))[i]]] for i in range(5)])
datasets=[b['实战']['无简词字词'] for b in bs]
table('词词与字词分账：实际出现次数',[[f]+[d.get(f,0) for d in datasets] for f in ['尝试打词次数','打词次数','词词原有非首选尝试次数','词词原有超三选拆词次数','实际打词中词词选重次数','单字新增词选重次数','单字导致有效词位后移次数','字占位导致拆词次数','词插入使字位后移次数','词插入新增字翻页键数']])
text='完整选重率含词词重码，不能直接视为布局造成的损失；字词增量影响率只统计单字与词混排导致的有效位次后移。位次后移不一定增加击键数。静态碰撞按字音—词对计数，实战按出现次数计数，两者分母不同。'
md+=['',text];ht+=['<p>'+text+'</p>']
for label,r in zip(labels,rs):
 for layer,mat in r['theory']['字词矩阵'].items():table(label+' '+layer+'：字词冲突对矩阵',[[cl]+row for cl,row in zip(['1–500','501–1500','1501–3000','3001–6000','6001–8454'],mat)],['字音频档 / 词频档','1–2000','2001–5000','5001–10000','10001–20000','20001–50000','50001–60000'])
ht+=['<p><a href="最终候选报告.html">查看五个候选的键盘热力图与布局文件</a></p>']
(P/'五个候选性能细节.md').write_text('\n'.join(md)+'\n',encoding='utf-8');(P/'五个候选性能细节.html').write_text(''.join(ht),encoding='utf-8')
for label,r,o in zip(labels,rs,opts):
 mat=r['theory']['字词矩阵'];print(label,r['id'],'total',sum(b['≤三码首选'] for b in r['theory']['分段']),'collisions',{k:sum(map(sum,v)) for k,v in mat.items()})
