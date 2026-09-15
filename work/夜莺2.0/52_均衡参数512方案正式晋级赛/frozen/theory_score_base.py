from pathlib import Path
import json,html,math
P=Path(__file__).resolve().parent; A=P.parent/'12_权重与步数对照'
rows=json.loads((A/'分段与分项汇总.json').read_text(encoding='utf-8'))
coll={r['组别']:r for r in json.loads((A/'字词碰撞分档汇总.json').read_text(encoding='utf-8'))}
raw={r['id']:r for r in json.loads((A/'manifest.json').read_text(encoding='utf-8'))['results']}
config_path=P/'计分规则.json'
if config_path.exists(): cfg=json.loads(config_path.read_text(encoding='utf-8'))
else:
 cfg={'版本':'草案1','类别满分':{'三码效率':35,'字词避重':25,'手感':25,'单字重码':10,'键位负担':5},'三码分段权重':[25,15,25,20,10,5],'字词字档权重':[35,30,20,10,5],'字词词档权重':[30,25,20,12,8,5],'字词每格半分冲突数':10,'字词实战占比':0.8,'说明':'固定标尺，不以参赛组的最大最小值归一化。损失项目得分=满分/(1+损失/半分标尺)。权重与标尺为设计草案，不是客观定律。'}
 config_path.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
assert sum(cfg['类别满分'].values())==100
out=[]
for r in rows:
 id=r['id']; f=raw[id]['metrics']['characters_short']; full=raw[id]['metrics']['characters_full']; entries=[]
 def add(cat,name,val,budget,scale=None):
  score=None if val is None else budget*(val if scale is None else 1/(1+val/scale))
  assert score is None or (-1e-8<=score<=budget+1e-8)
  entries.append({'类别':cat,'项目':name,'原值':val,'满分':budget,'半分标尺':scale,'得分':score})
 for b,w in zip(r['分段'],cfg['三码分段权重']):
  budget=35*w/100
  if b['字频覆盖'] is None:
   add('三码效率',b['区间']+' ≤三码数量率（本段无分配频率）',b['数量占比'],budget)
  else:
   add('三码效率',b['区间']+' ≤三码数量率',b['数量占比'],budget*0.5)
   add('三码效率',b['区间']+' ≤三码字频覆盖',b['字频覆盖'],budget*0.5)
 for name,mat in coll[id]['矩阵'].items():
  mix=cfg['字词实战占比'] if name=='剔除有简码字音项' else 1-cfg['字词实战占比']
  for i,row in enumerate(mat):
   for j,n in enumerate(row):
    add('字词避重',name+f' 字档{i+1}×词档{j+1}',n,25*mix*cfg['字词字档权重'][i]/100*cfg['字词词档权重'][j]/100,cfg['字词每格半分冲突数'])
 # 当前引擎向量后两项未实现，不能因恒零得满分。
 for i,name,budget,scale in [(0,'同手率（互击的互补项）',2,.5),(1,'同指大跨排',5,.01),(2,'同指小跨排',4,.08),(3,'小指干扰',3,.05),(4,'错手',1,.02),(5,'三连击',2,.001)]:
  add('手感',name,f['fingering'][i],budget,scale)
 for name,val,budget,scale in [('键对当量',f['pair_equivalence'],3,1.3),('音形交界当量',f['phonetic_shape_transition_equivalence'],3,.45),('实际加权键长超出2键的部分',max(0,r['加权实际键长']-2),2,1)]: add('手感',name,val,budget,scale)
 add('单字重码','实际全码选重率',full['effective_duplication'],8,.001)
 add('单字重码','纸面全码选重率',full['duplication'],2,.08)
 add('键位负担','键位分布损失（引擎既定目标）',f['key_distribution_loss'],3,.4)
 dist=f['key_distribution'];left=sum(dist.get(k,0) for k in 'qwertasdfgzxcvb')
 add('键位负担','左右手负担偏离50%',abs(left-.5),1,.05)
 add('键位负担','最高单键使用占比',max(dist.values()),1,.1)
 totals={k:sum(x['得分'] for x in entries if x['类别']==k) for k in cfg['类别满分']}
 assert abs(sum(x['满分'] for x in entries)-100)<1e-8
 out.append({'组别':id,'分类得分':totals,'总分':sum(totals.values()),'分项':entries})
out.sort(key=lambda r:-r['总分'])
(P/'量化结果.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
intro='草案1：100分制。三码35分、字词避重25分、手感25分、单字重码10分、键位负担5分。该分数表达这份草案的取舍，不是客观质量或原退火分数；未修改退火程序。'
notes=['三码：六档依次为1–300、301–500、501–1500、1501–3000、3001–6000、6001–8454；档内数量率与字频覆盖各占一半，末档未分配频率仅计数量率。三简率采用≤三码首选，不是恰好三键。','字词：五字档为1–500、501–1500、1501–3000、3001–6000、6001–8454；六词档为1–2000、2001–5000、5001–10000、10001–20000、20001–50000、50001–60000。每格单独计分，有简让全后占80%，全部全码占20%。这些交叠视角的配比是有意设置，不是独立事件相加。','固定公式：覆盖类得分=该项满分×覆盖率；损失类得分=该项满分÷(1+原值÷半分标尺)。冲突格暂定10对得到该格一半分数，0对满分；格子预算由字档和词档权重相乘。这个标尺需要你审定。','所有统计按当前同一字音集与词库可比。换词库或字频须统一重算全部候选。频率空缺不等于实际零频。','尚未单独计分：同键四连、同指三连/四连的独立统计、扩展当量等当前未提供或未分离的项目；当前三连击是引擎原有定义。纸面全码分层手感、累计层级与总体重复指标保留原报告用于核对，不重复加分。故这是可用初稿，尚非全部期望指标都已测齐。','不采用当批最高/最低映射0–100；新增候选不会改变旧候选分数。原始各项和参数保留，可后续调权；硬性规则验证仍是入围条件，不能拿总分抵消规则违规。']
page=['<!doctype html><meta charset="utf-8"><title>夜莺2.0量化计分草案</title><style>body{font-family:system-ui;background:#f4f7fb;color:#213448;padding:28px}table{border-collapse:collapse;background:white;margin:20px 0}td,th{border:1px solid #ccd9e5;padding:9px;text-align:right}th{background:#e1edf7}p{max-width:1200px;line-height:1.8}summary{font-size:20px;cursor:pointer;padding:12px}</style><h1>量化计分表 · 草案1</h1><p>'+intro+'</p>']
page+=['<p>'+html.escape(n)+'</p>' for n in notes]
page+=['<table><tr><th>组别</th>'+''.join('<th>'+k+'</th>' for k in cfg['类别满分'])+'<th>总分</th></tr>']
for r in out:page+=['<tr><td>'+r['组别']+'</td>'+''.join(f'<td>{v:.3f}</td>' for v in r['分类得分'].values())+f'<td><b>{r["总分"]:.3f}</b></td></tr>']
page+=['</table>']
for r in out:
 page+=['<details><summary>'+r['组别']+'：查看各档各项</summary><table><tr><th>类别</th><th>项目</th><th>原值</th><th>满分</th><th>半分标尺</th><th>得分</th></tr>']
 for e in r['分项']:page+=['<tr>'+''.join('<td>'+html.escape(f'{v:.6f}' if isinstance(v,float) else str(v) if v is not None else '覆盖类')+'</td>' for v in e.values())+'</tr>']
 page+=['</table></details>']
(P/'量化计分表.html').write_text(''.join(page),encoding='utf-8')
(P/'计分说明.md').write_text('# 量化计分草案1\n\n'+intro+'\n\n'+'\n\n'.join(notes),encoding='utf-8')
print([(r['组别'],round(r['总分'],3)) for r in out])
