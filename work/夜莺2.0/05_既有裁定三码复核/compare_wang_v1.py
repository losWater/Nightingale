from pathlib import Path
import json,runpy,html,hashlib
from collections import defaultdict
HERE=Path(__file__).resolve().parent
p=HERE.parent/'04_逐根删除评估/review_three_codes.py'
n={'__file__':str(p)};exec(p.read_text(encoding='utf-8').split('ledgerpath=')[0],n)
double=runpy.run_path(str(p.parent.parent/'03_字音频率审计/rebuild.py'))['double_code']
source=HERE.parents[2]/'releases/v1.0/01_正式码表/夜莺1.0字词表_码前.txt'
codes=defaultdict(list);rank=defaultdict(int)
for line in source.read_text(encoding='utf-8-sig').splitlines():
 bits=line.split('\t')
 if len(bits)!=2:continue
 code,c=bits;rank[code]+=1
 if len(c)==1:codes[c].append((code,rank[code]))
labels={n['og'](n['rid'](x)):x for x in ['王','丰']};b=defaultdict(lambda:defaultdict(list))
for c,seq in n['BASE'].items():
 g=labels.get(n['og'](seq[0]))
 if g:
  for s in n['readings'][c]:b[s][g].append(c)
risk=[];single=[]
for s,gs in b.items():
 if len(gs)<2:continue
 old=[]
 for g,cs in gs.items():
  for c in cs:
   short=[code for code,r in codes[c] if len(code)==3 and code[:2]==double(s) and r==1]
   if short:old.append({'字':c,'原三简':short,'原根组':g,'分音频次':n['freq'][s,c],'更短首选':[code for code,r in codes[c] if len(code)<3 and r==1 and (len(code)==1 or code==double(s))]})
 if not old:continue
 old.sort(key=lambda x:(-x['分音频次'],x['字']))
 item={'音节':s,'原三简字':old,'至少让位数':max(0,len(old)-1),'较低频次合计':sum(x['分音频次'] for x in old[1:])}
 if len({x['原根组'] for x in old})>=2:risk.append(item)
 else:single.append(item)
risk.sort(key=lambda x:(-x['较低频次合计'],x['音节']));single.sort(key=lambda x:x['音节'])
notes='对照夜莺1.0正式字词码表的三码首选（包含词的真实候选顺序），按对应音节核对。只看王玉玨与丰龶合并的假设，不加主、不移动举字底，该方案已确认纳入2.0累计试算，待统一实装。直接风险为不同原根组各有实际三简，合并后同一音节只剩一个自然三码首选位置。谁让位尚未裁决；表按当前分音频次排序，不以此替换1.0人工选择。未重新安排一二简、实际键位或容错码。单字形态分析沿用当前2.0试算，完整候选组含其他变化；本报告隔离王丰合并新增的跨组竞争。'
data={'说明':notes,'直接风险组数':len(risk),'涉及读音项':sum(len(x['原三简字']) for x in risk),'涉及不同汉字数':len({c['字'] for x in risk for c in x['原三简字']}),'至少让位读音项':sum(x['至少让位数'] for x in risk),'直接风险':risk,'仅一个现有三简':single,'来源':str(source),'SHA256':hashlib.sha256(source.read_bytes()).hexdigest()}
(HERE/'王丰组对照1.0实际三简.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
md=['# 对照夜莺1.0实际三简','',notes,'',f"直接风险{len(risk)}组，涉及{data['涉及不同汉字数']}字，至少{data['至少让位读音项']}个读音项需要另安排码位。",'','| 音节 | 原三简字与码 | 原根组 |','|---|---|---|']
for x in risk:md.append('| '+x['音节']+' | '+'、'.join(c['字']+' '+','.join(c['原三简']) for c in x['原三简字'])+' | '+'、'.join(c['原根组'] for c in x['原三简字'])+' |')
md+=['','只有一个现有三简的音节：'+ '；'.join(x['音节']+'：'+','.join(c['字']+' '+','.join(c['原三简']) for c in x['原三简字']) for x in single)+'。保留原三简优先时，这些不必因本次合并让位。']
(HERE/'王丰组对照1.0实际三简.md').write_text('\n'.join(md),encoding='utf-8')
esc=html.escape
page='<!doctype html><meta charset="utf-8"><title>王丰组对照1.0实际三简</title><style>body{font:16px/1.7 Microsoft YaHei,sans-serif;margin:32px;color:#233548;background:#f5f7fa}table{border-collapse:collapse;background:white}th,td{border:1px solid #cdd9e0;padding:8px 18px}p{max-width:1100px}</style><h1>对照夜莺1.0实际三简</h1><p>'+esc(notes)+'</p><p>'+esc(md[4])+'</p><table><tr><th>音节</th><th>1.0三简与原根组</th></tr>'
for x in risk:page+='<tr><td>'+esc(x['音节'])+'</td><td>'+esc('；'.join(c['字']+' '+','.join(c['原三简'])+'（'+c['原根组']+'）' for c in x['原三简字']))+'</td></tr>'
page+='</table><p>'+esc(md[-1])+'</p>'
(HERE/'王丰组对照1.0实际三简.html').write_text(page,encoding='utf-8')
print(data['直接风险组数'],data['涉及不同汉字数'],data['至少让位读音项'])
for x in risk:print(x['音节'],' / '.join(c['字']+' '+','.join(c['原三简']) for c in x['原三简字']))
