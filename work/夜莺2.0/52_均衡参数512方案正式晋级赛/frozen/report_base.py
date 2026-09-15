from pathlib import Path
import json,html
from benchmark import P,read,write
old={r['组别']:r for r in read(P.parent/'13_量化计分/量化结果.json')}
results=[read(f) for f in sorted((P/'results').glob('*/结果.json'))]
scorecfg={'版本':'草案3_字词词词分离','理论占比':.6,'实战占比':.4,'纯单字实战占比':.5,'无简词实战占比':.5,'理论当量满分':{'键均当量':1,'字均当量':2},'实战满分':{'键盘负担':40,'当量':30,'码长':20,'字字选重':5,'字词增量影响':5},'说明':'理论替换草案1中键对当量3分为统一当量3分；保留理论100分制。实战每种模式100分，热力负担40、当量30、码长20、字字选重5、字词增量影响5。总分=理论60%+双模式平均40%。主观权重初稿。'}
write(P/'实战计分规则.json',scorecfg)
def s(x,b,scale):return None if x is None else b/(1+x/scale)
summary=[]
for r in results:
 t=r['理论当量_统一46键表'];eligible=not t['缺失当量键对'] and not t['缺字音频次'] and all(v['可计分'] for v in r['实战'].values())
 prev=old.get(r['组别']);oldpair=next(e['得分'] for e in prev['分项'] if e['项目']=='键对当量') if prev else None
 td={'键均当量':s(t['键均当量'],1,1.3),'字均当量':s(t['字均当量'],2,3)}
 theory=prev['总分']-oldpair+sum(td.values()) if prev and eligible else None
 ms={}
 for name,d in r['实战'].items():
  sc={'热力·左右负担':s(abs(d['左手占比_不含空格']-.5),10,.05),'热力·小指负担':s(d['小指占比_不含空格'],10,.2),'热力·最高单键':s(d['最高单键占比_不含空格'],10,.1),'热力·最高单指':s(d['最高单指占比_不含空格'],10,.25),'键均当量':s(d['键均当量'],10,1.3),'字均当量':s(d['字均当量'],20,4),'码长':s(max(0,d['每字击键']-1),20,2),'字字选重':s(d['字字选重率_单字上屏'],5,.02),'字词增量影响':s(d['字词增量受影响率'],5,.02)}
  ms[name]={'分项':sc,'总分':sum(v for v in sc.values() if v is not None) if d['可计分'] else None}
 total=.6*theory+.4*sum(x['总分'] for x in ms.values())/2 if theory is not None and eligible else None
 r['计分']={'理论旧分':prev['总分'] if prev else None,'理论统一当量分项':td,'理论新分':theory,'实战':ms,'综合分':total,'状态':'模拟分（多音默认项未逐句校准）' if eligible else '不可计分'}
 summary.append(r)
summary.sort(key=lambda r:r['计分']['综合分'] if r['计分']['综合分'] is not None else -1,reverse=True)
write(P/'双模式计分汇总.json',summary)
notes=['词词重码单列展示，不直接扣冲突分。原选重10分拆为字字选重5分与字词增量影响5分；字词增量=词插入导致单字位后移＋原本三选内可打的词被单字挤后，每次目标只记一次。原本词词重码已超过三选的词，不因单字继续挤后再扣分。完整按键、当量、热力与码长仍保留全部实际成本。','固定10000句、155026字次，来自百科、传媒、网文、对话；去重文本9966条。继承旧长度分层样本，含34个重复文本，不是自然文章长度分布。所有方案使用同一输入哈希和固定分词。','配套词库固定60000个二字词，每词四码，无简词、无辅助码、无动态调频。混排顺序：无该音简码的单字→词→有该音简码的单字；各类内部沿用冻结排序。纯单字移除所有词，不重新抢占原简词预留位。','单字有简打简：按最短编码，再按候选位；保留每个字的固定语料读音，不允许选更短的其他读音。词组最长匹配，位≤3打词，超过3选拆单，不尝试辅助码。比较的是固定打法，不是最少击键的全局最优解。','所有编码都加显式上屏键，包括四码首选：1选空格、2选分号、3选引号；每页3候选，后续页以等号翻页后按实际余位选字。没有启用四码自动上屏；不是某一个Rime客户端的逐事件实测。标点本身不计按键，但不跨标点组词；保留字词之间相邻按键，不跨句连接。','理论当量：每个字音的最短码+上屏键，独立统计内部键对，再按冻结字音频率加权。实战当量：逐句完整按键流。两者同用论文46键当量表；总当量除以已知键对数为键均当量，除以汉字次数为字均当量。理论不包含字际转接，实战包含，因此数值不要求相等。缺失当量必须显示，缺失时不计完整总分。','热力图颜色统一以10%为上限，每键显示次数与占比。全键图包含空格、选重、翻页；编码键图只看编码字母。各指统计以B归左食指，空格独立计拇指，不强行归左手或右手。','11039个多音字次尚用默认音；其余按固定词读音或单读音。所有组相同，但不等同逐句人工标音。结果为模拟初稿；该词库曾用于优化，不作为未见词库泛化证据。','计分草案：理论60%，实战40%（两种模式各一半）。实战各100分：键盘负担40、当量30、码长20、字字选重5、字词增量影响5。键盘负担由左右偏差、小指、最高键、最高指各10分组成；不是要求每根手指平均。得分=预算/(1+原值/标尺)。理论统一当量替换原键对当量3分，避免直接叠加旧项。','大/小跨排、连击及字词冲突次数均输出；本版实战不把这些与当量、选重再重复加分，是否单独分配预算留待调权。字词碰撞不一定导致选重，所以同时列尝试次数、位次后移和退词次数。']
page=['<!doctype html><meta charset="utf-8"><title>固定语料实战与当量计分</title><style>body{font-family:system-ui;background:#f4f7fb;color:#213448;margin:28px}p{max-width:1300px;line-height:1.7}table{border-collapse:collapse;background:white;margin:16px 0}td,th{border:1px solid #cbd8e5;padding:8px;text-align:right}th{background:#dfeaf4}summary{font-size:21px;cursor:pointer;padding:12px}.keyboard{padding:12px;background:#dae2ea;display:inline-block;border-radius:12px}.row{display:flex;gap:5px;margin:5px}.key{width:70px;height:62px;display:flex;flex-direction:column;justify-content:center;text-align:center;border:1px solid #adc0d2;border-radius:6px;font-size:15px}.key small{font-size:11px}.space{width:260px}</style><h1>固定语料双模式实战 · 当量与热力图</h1>']
page+=['<p>'+html.escape(n)+'</p>' for n in notes]
page+=['<table><tr><th>组别</th><th>理论分</th><th>单字实战分</th><th>字词实战分</th><th>综合分</th></tr>']
fmt=lambda v:'待补' if v is None else f'{v:.4f}'
for r in summary:
 c=r['计分'];page+=['<tr><td>'+r['组别']+'</td>'+''.join('<td>'+fmt(v)+'</td>' for v in [c['理论新分'],*[x['总分'] for x in c['实战'].values()],c['综合分']])+'</tr>']
page+=['</table>']
for r in summary:
 page+=['<details><summary>'+r['组别']+'</summary><table><tr><th>项目</th><th>理论独立单字</th><th>实战纯单字</th><th>实战无简词字词</th></tr>']
 datasets=[r['理论当量_统一46键表'],*r['实战'].values()]
 for field in ['每字击键','键均当量','字均当量','当量覆盖率','选重率_每次上屏','字字选重次数','字字选重率_单字上屏','字词增量受影响率','词词原有非首选尝试次数','词词原有超三选拆词次数','实际打词中词词选重次数','单字新增词选重次数','单字导致有效词位后移次数','词插入使字位后移次数','词插入新增字翻页键数','大跨排率','小跨排率','同键三连率','同键四连率','同指三连率','同指四连率','左手占比_不含空格','小指占比_不含空格','尝试打词次数','打词次数','词遇字同码次数','单字遇词同码次数','字占位导致词位后移次数','字占位导致拆词次数','缺字音字次']:
  page+=['<tr><th>'+field+'</th>'+''.join('<td>'+fmt(d.get(field))+'</td>' for d in datasets)+'</tr>']
 page+=['</table>']
 for mode,d in r['实战'].items():
  for kind,counts in [('全部按键',d['按键次数']),('编码键',d['编码键热力'])]:
   total=sum(counts.values());page+=['<h3>'+mode+' · '+kind+'</h3><div class="keyboard">']
   for row in ['1234567890-=','qwertyuiop[]',"asdfghjkl;'",'zxcvbnm,./',' ']:
    page+=['<div class="row">']
    for k in row:
     n=counts.get(k,0);v=n/max(total,1);color=f'hsl(208 70% {98-55*min(v/.1,1):.1f}%)';label='空格' if k==' ' else k
     page+=['<div class="key '+('space' if k==' ' else '')+'" style="background:'+color+'">'+html.escape(label)+f'<small>{n:,}次 · {v:.2%}</small></div>']
    page+=['</div>']
   page+=['</div>']
  page+=['<h3>'+mode+' · 分项计分</h3><table>']
  for k,v in r['计分']['实战'][mode]['分项'].items():page+=['<tr><th>'+k+'</th><td>'+fmt(v)+'</td></tr>']
  page+=['</table>']
 page+=['</details>']
(P/'固定语料实战计分.html').write_text(''.join(page),encoding='utf-8')
(P/'测评规则与使用说明.md').write_text('# 固定语料双模式测评\n\n'+'\n\n'.join(notes)+'\n\n## 使用\n\n`python benchmark.py --table <Chai五列code.txt绝对路径> --name <方案名>`\n\n`python report.py` 生成全部结果的热力图与评分。单字表五列为字、全码、全码序号（0起）、最短码、最短码序号（0起）；多字行忽略。额外的新方案无理论第一部分成绩时，先输出实战分，综合分待补，不会当成零分。\n\n`python benchmark.py --all` 对已完成的七组试跑批量测试。固定清单含SHA256，输入不一致即停止。不可覆盖旧结果名来混淆版本。\n\n旧脚本与研究提纲保留于inputs。当量参考表来源为形码盒子，见文件头与旧手感统计.py。\n',encoding='utf-8')
print([(r['组别'],r['计分']['综合分']) for r in summary])
