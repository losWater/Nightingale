from pathlib import Path
import json,html,hashlib
P=Path(__file__).resolve().parent
R=lambda p:json.loads(p.read_text(encoding='utf-8'))
assert all(R(P/n)['status']=='complete' for n in ['status.json','rotation_status.json','parameter_status.json'])
files=list((P/'jobs').glob('*/round2.json'));assert len(files)==92
ds={}
for f in files:
 d=R(f);o=R(f.parent/'optimized.json');assert o['cache_delta']<1e-7
 assert all(x['可计分'] and not x['缺字音字次'] for x in d['benchmark']['实战'].values())
 assert abs(d['score']['total']-(.6*d['score']['theory']+.2*sum(x['score'] for x in d['score']['practice'].values())))<1e-9
 ds[d['card']['id']]=d
profiles=R(P/'parameter_profiles.json');layouts={}
for c in [c for c in R(P/'cards.json') if c['id'].startswith('parameter_')]:
 cfg=R(Path(c['original_config']));h=hashlib.sha256(json.dumps(cfg['form']['mapping'],sort_keys=True).encode()).hexdigest();key=(c['start_kind'],c['seed'])
 if key in layouts:assert layouts[key]==h
 else:layouts[key]=h
 assert cfg['optimization']==profiles[c['profile']]['config']['optimization']
data=R(P/'参数集稳定性.json');rows=[]
for r in data['概览']:
 m=data['完整统计'][str(r['参数集'])]['指标统计']
 rows.append({'参数集':r['参数集'],'平均分':r['平均综合分'],'最差分':r['最差综合分'],'标准差':r['标准差'],'前300通过率':r['前300无有效重码通过率'],'前6000三码均值':sum(v['mean'] for k,v in m.items() if k.endswith('·三码首选') and not k.startswith('6001')),'纯字选重次数均值':m['纯单字·字字选重次数']['mean'],'纯字字均当量':m['纯单字·字均当量']['mean'],'字词增量影响率':m['无简词字词·字词增量受影响率']['mean']})
changes=[]
keys=['每字击键','字均当量','键均当量','字字选重率_单字上屏','字词增量受影响率','大跨排率','小跨排率','最高单键占比_不含空格','小指占比_不含空格','左手占比_不含空格']
for id,d in ds.items():
 c=d['card'];parent=c.get('parent')
 if id.startswith('parameter_'):parent='parameter_3_'+id.split('_',2)[2]
 if parent and parent in ds:base=ds[parent];label=parent
 else:
  label=c['tag']+'既有×1.25（非直接父方案）';base=R(P.parent/'21_手感权重微调/jobs'/f'{c["tag"]}_hand1.25/round2.json')
 gains=[];losses=[]
 for mode,b in d['benchmark']['实战'].items():
  for k in keys:
   a=base['benchmark']['实战'][mode][k];z=b[k];diff=abs(z-.5)-abs(a-.5) if k=='左手占比_不含空格' else z-a
   if abs(diff)>1e-12:(gains if diff<0 else losses).append(f'{mode}·{k}: {a:.6g} → {z:.6g}')
 changes.append({'方案':id,'参照':label,'综合分变化':d['score']['total']-base['score']['total'],'改善':gains,'退步':losses})
(P/'逐次改善与退步.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
def table(rs):
 ks=list(rs[0]);return '<table><tr>'+''.join('<th>'+k+'</th>' for k in ks)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(f'{r[k]:.6f}' if isinstance(r[k],float) else str(r[k]))+'</td>' for k in ks)+'</tr>' for r in rs)+'</table>'
body='''<h1>退火参数集：本轮结论</h1><p>92次完成：36次分批探索、24次轮换、32次参数集验证。全部通过重新编码、评分合计、无缺字音实战核验；参数验证使用相同四类起点各两次，每套8次，比较参数稳定性，不按幸运单张冠军决策。</p>
<h2>保留不同取舍</h2><p><b>参数0，均衡候选：</b>前3000保护、全域字频有效重码权重300、手感×1.5。平均分比对照高约0.324，综合分标准差较小；但平均实战选重略多、三码数量略少，字词影响率也没有优势。不能称全面升级。</p><p><b>参数1，近似备选：</b>前3000保护、全域字频有效重码权重300、手感×1.25。平均分比参数0只高0.015，差别远小于本批波动，不足以宣布更优。</p><p><b>参数3，必须保留的对照：</b>前6000保护、全域字频有效重码权重0、手感×1.25。平均综合分略低，但本批平均三码和实战选重次数更好。参数2的平均字词增量影响率较好，保留作该方向备选。</p>'''
body+='<h2>重复验证结果</h2>'+table(rows)
body+='''<h2>限制</h2><p>没有一个参数集在所有指标上胜出。前300通过率100%仅指本次8次全部通过，不是未来保证。原生随机流未固定；同一万句反复用于开发，不作为独立泛化证据。评分提高不能替代逐项收益审查。尚不能声称超过夜莺1.0，也不将历史单张冠军与本批平均混比。</p><h2>交付</h2><p><a href="参数集验证.html">参数验证概览</a> · <a href="参数集稳定性.json">各指标均值与波动</a> · <a href="逐次改善与退步.json">92次改善/退步记录</a></p><p>参数文件仅含搜索参数，需配合本批冻结根集、元素、编码与简码约定；没有改写正式默认配置或发布包。本轮结束，不无界追加搜索。</p>'''
for i in range(4):body+=f'<p><a href="参数集交付/profile_{i}.json">下载参数集{i}</a></p>'
(P/'参数集最终总结.html').write_text('<!doctype html><meta charset="utf-8"><title>参数集最终总结</title><style>body{font:16px system-ui;margin:32px;background:#f3f6fa;color:#213047}p{max-width:1100px;line-height:1.8}table{border-collapse:collapse}td,th{padding:9px;border:1px solid #cbd5e1}</style>'+body,encoding='utf-8')
f=P/'进度与结果.html';s=f.read_text(encoding='utf-8');s=s.replace('<h1>自动分批细化</h1>','<h1>自动分批细化：92次已完成</h1><p><a href="参数集最终总结.html">查看参数集最终总结</a>：包括基础探索、轮换与参数验证，交付对象是参数集。</p>');f.write_text(s,encoding='utf-8')
(P/'完成核验.json').write_text(json.dumps({'已完成运行':92,'参数验证次数':32,'参数集数量':4,'同起点配对':True,'重编码缓存一致':True,'实战完整':True,'评分合计一致':True,'候选':0,'保留对照':3},ensure_ascii=False,indent=2),encoding='utf-8')
print('92 runs verified; summary written')
