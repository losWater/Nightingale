from pathlib import Path
from collections import Counter,defaultdict
import json,yaml,hashlib
O=Path(__file__).resolve().parent;P=O.parent;R=P.parents[1]
a=json.loads((O/'manifest.json').read_text(encoding='utf-8'));assert a['status']=='short_run_complete'
es=yaml.safe_load((O/'elements.yaml').read_text(encoding='utf-8'));chars=[e for e in es if len(e['词'])==1];freq=[e['频率'] for e in chars]
oldslots={}
for l in (R/'releases/v1.0/01_正式码表/夜莺1.0字词表.txt').read_text(encoding='utf-8-sig').splitlines():
 s=l.split('\t')
 if len(s)==2 and len(s[1])<=2:oldslots.setdefault(s[1],s[0])
left=set('qwertasdfgzxcvb');fingers={k:(0 if k in left else 1,i) for ks,i in [('qaz',0),('wsx',1),('edc',2),('rtfgvb',3),('yuhjnm',3),('ik',2),('ol',1),('p',0)] for k in ks}
selectedcodes={json.loads(l)['实验码'] for l in (P/'09_字词避重选词实验/常用加补位词集.jsonl').open(encoding='utf-8')}
report=[]
for r in a['results']:
 out=Path(r['output']);met=json.loads((out/'metric.json').read_text(encoding='utf-8'))['metric']
 rows=[l.split('\t') for l in (out/'code.txt').read_text(encoding='utf-8').splitlines()]
 slots={x[3]:x[0] for x in rows if len(x[3])<=2 and int(x[4])==0}
 changes=[{'码位':c,'1.0':oldslots.get(c),'2.0':slots.get(c)} for c in sorted(oldslots.keys()|slots.keys()) if oldslots.get(c)!=slots.get(c) and (c in slots or len(c)==1)]
 (out/'一二简变化.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
 hot=Counter();events=Counter();total=sum(freq);keys=0;physical=0;cw=0;paper=0
 for e,x in zip(chars,rows):
  f=e['频率'];code=x[3]
  for k in code:
   if k in fingers:hot[k]+=f;keys+=f
  physical+=f*(len(code)+(len(code)<4 or int(x[4])>0))
  if x[1] in selectedcodes:
   paper+=1
   if len(code)==4:cw+=1
  for n in [3,4]:
   for i in range(len(code)-n+1):
    seq=code[i:i+n]
    if len(set(seq))==1:events[f'同键{n}连']+=f
    if all(k in fingers for k in seq) and len({fingers[k] for k in seq})==1:events[f'同指{n}连']+=f
 summary={'id':r['id'],'初分':r['initial_score'],'终分':r['final_score'],'移动根组':r['changed_groups'],'三码覆盖':r['final']['三码及以内首选字频覆盖'],'起点三码覆盖':r['initial']['三码及以内首选字频覆盖'],'加权实际键长':physical/total,'大跨':met['characters_short']['fingering'][1],'小跨':met['characters_short']['fingering'][2],'小指干扰':met['characters_short']['fingering'][3],'全码有效选重率':met['characters_full']['effective_duplication'],'字词实际碰撞字音项':cw,'纸面碰撞字音项':paper,'左手比例':sum(v for k,v in hot.items() if k in left)/keys,'键热度':{k:v/keys for k,v in hot.items()},'连击每字频加权次数':{k:v/total for k,v in events.items()},'一二简变化数':len(changes),'补三简入口':r['final']['补三简入口'],'原生分项':met}
 report.append(summary)
(O/'分项汇总.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 夜莺2.0首轮短程试跑','', '状态：6个起点各3000步完成，使用134根组、8454字音身份、48046个词码位目标。所有起点通过独立简码占位、有简让全排序和最终配置重新编码验证。增量与全量分数误差均小于1e-7。','', '## 结果','', '|起点|初始分数|最终分数↓|改变根组数|≤三码首选字频覆盖|大跨率|小跨率|字词碰撞字音项|','|---|---:|---:|---:|---:|---:|---:|---:|']
for r in report:lines.append(f'|{r["id"]}|{r["初分"]:.2f}|{r["终分"]:.2f}|{r["移动根组"]}|{r["三码覆盖"]:.2%}|{r["大跨"]:.2%}|{r["小跨"]:.2%}|{r["字词实际碰撞字音项"]}|')
lines += ['', '## 重要口径','', '- 分数越低越好，采用历史核心权重作为试跑初值，并按新词码位的平均排序指数归一化字词目标。不是正式权重定稿。','- 三码覆盖按最短可用码且首选统计；补三简只导出入口，不重复计字频、收益。','- 字词碰撞项为本轮词码位与无更短简码字音的交集计数，不是词对数，也不是高频红区统计。','- 第六个起点采用击的另一拆法；其他五个采用二山。种子只固定初始布局，原生搜索随机流尚未固定，不能称作可逐步复现。','- 使用已审计分读音字频，含已标注的待分配量；本轮新词库排序没有擅自回灌为单字字频。','- 1.0投影是新根组合并后按旧键多数确定的合法初始布局，不是原样1.0。','- 原生大跨、小跨、小指等指标用于同口径对照；附加键热度和三四连按常规指法（B左食指），未混入历史B右食指口径。','- 报告含全部原生分层指标。全码与简码组合当量、热度和其他指法目前部分为零权重观察项，核心优化仍为三码数量、加权跨排、有效全码与字词碰撞、音形衔接；不能宣称所有观察项都有独立非零权重。','- 当前只完成短跑，不能据此宣称优于1.0正式版或已找到最终布局。','', '## 文件','', '- 分项汇总.json：全部原生与附加分项。','- 各起点short_run/output目录：码表、补三简入口、一二简变化、指标。','- 各起点verify/run.json：含搜索空间的可重新编码最终配置。','- temperature.json：实际单根损失小样与初始温度。','- manifest.json：起点、种子、根组投影、验证状态。']
(O/'试跑结果.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
files=[O/'elements.yaml',O/'elements_ji_ju.yaml',O/'build_trial.py',O/'run_trial.py',O/'temperature.json',Path('E:/nightingale2-build/release/chai.exe')]
(O/'运行指纹.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{k:v for k,v in r.items() if k not in ['原生分项','键热度','连击每字频加权次数']} for r in report],ensure_ascii=False))
