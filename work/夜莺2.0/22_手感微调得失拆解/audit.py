from pathlib import Path
import json,html
W=Path(__file__).resolve().parent.parent;P=Path(__file__).resolve().parent
mapping={'热力左右':'左手占比_不含空格','热力小指':'小指占比_不含空格','热力最高键':'最高单键占比_不含空格','热力最高指':'最高单指占比_不含空格','键均当量':'键均当量','字均当量':'字均当量','码长':'每字击键','字字选重':'字字选重率_单字上屏','字词增量':'字词增量受影响率'}
def load(folder,id):return json.loads((W/folder/'jobs'/id/'round2.json').read_text(encoding='utf-8'))
def flatten(d):
 rows=[]
 for r in d['theory']['theory_old']['分项']:
  if r['项目']=='键对当量':continue
  rows.append({'类别':'理论·'+r['类别'],'项目':r['项目'],'原值':r['原值'],'贡献':.6*r['得分']})
 t=d['benchmark']['理论当量_统一46键表']
 for k,b,s in [('键均当量',1,1.3),('字均当量',2,3)]:rows.append({'类别':'理论·手感','项目':'统一46键·'+k,'原值':t[k],'贡献':.6*b/(1+t[k]/s)})
 for mode,parts in d['score']['practice'].items():
  for k,v in parts['parts'].items():rows.append({'类别':mode,'项目':k,'原值':d['benchmark']['实战'][mode][mapping[k]],'贡献':.2*v})
 assert abs(sum(r['贡献'] for r in rows)-d['score']['total'])<1e-9
 return {(r['类别'],r['项目']):r for r in rows}
def table(rows):
 keys=list(rows[0]);return '<table><tr>'+''.join('<th>'+html.escape(k)+'</th>' for k in keys)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(f'{r[k]:.6f}' if isinstance(r[k],float) else str(r[k]))+'</td>' for k in keys)+'</tr>' for r in rows)+'</table>'
page='<!doctype html><meta charset="utf-8"><title>手感微调得失拆解</title><style>body{font:16px system-ui;background:#f3f6fa;color:#213047;margin:32px}table{border-collapse:collapse;background:white;margin:20px 0}td,th{padding:9px;border:1px solid #cbd5e1}p{max-width:1100px;line-height:1.8}</style><h1>原权重 → 手感×1.25：综合分扣在哪里</h1><p>保持既有公式不变。所有贡献已乘理论60%、双实战各20%，正数加分，负数扣分；逐项相加与最终总分变化一致，误差小于1e-9。理论键对当量按实际统一46键替换后的公式计算，未误用旧分项。字词表每格的字档与词档均为互斥分段，不是累计。</p><p>D组最大损失来自有效单字重码；其纯单字实战字字选重从186次增到363次，说明存在实际退步。当量改善并不意味着选重减少。权重不变也不保证指标不变；现有退火对全域有效重码权重为0，仅前300有效重码有非零惩罚，这与最终评分的全域有效选重项存在差别。</p>'
output={}
for tag in ['A','D']:
 a=load('20_手感权重五万步对照',tag+'_hand1');b=load('21_手感权重微调',tag+'_hand1.25');aa=flatten(a);bb=flatten(b);assert aa.keys()==bb.keys()
 rows=[{'类别':k[0],'项目':k[1],'原权重原值':aa[k]['原值'],'×1.25原值':bb[k]['原值'],'原贡献':aa[k]['贡献'],'新贡献':bb[k]['贡献'],'综合分变化':bb[k]['贡献']-aa[k]['贡献']} for k in aa];rows.sort(key=lambda r:r['综合分变化'])
 cats={}
 for r in rows:cats[r['类别']]=cats.get(r['类别'],0)+r['综合分变化']
 delta=b['score']['total']-a['score']['total'];assert abs(sum(cats.values())-delta)<1e-9
 output[tag]={'总分变化':delta,'类别变化':cats,'逐项':rows}
 page+=f'<h2>{tag}组：{a["score"]["total"]:.6f} → {b["score"]["total"]:.6f}（{delta:+.6f}）</h2>'+table([{'类别':k,'综合分变化':v} for k,v in cats.items()])+ '<h3>所有分项：从最大损失到最大收益</h3>'+table(rows)
page+='<h2>如何解释</h2><p>D组理论有效全码选重率0.02162%→0.05477%，绝对增加0.03315个百分点；该项按8/(1+率/0.001)再乘60%计入总分，因此损失约0.845分。这个非线性标尺确实敏感，但实战选重接近翻倍，不能说只是评分假象。半分标尺0.001是否符合使用偏好，可后续独立讨论，本次未更改。</p><p>下一步优先核对全域/高频有效重码保护与实战损失，而不是继续增加手感倍率；可以保留×1.25作候选方向，先补一个与选拔口径一致的重码约束或惩罚做小对照。两起点单次运行不能证明因果或稳定收益。</p>'
(P/'得失拆解.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8');(P/'得失拆解.html').write_text(page,encoding='utf-8')
for tag,d in output.items():print(tag,d['总分变化'],d['类别变化'])
