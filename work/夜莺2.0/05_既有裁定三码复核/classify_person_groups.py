from pathlib import Path
from collections import defaultdict
from itertools import combinations
import json, html

HERE=Path(__file__).resolve().parent
source=HERE.parent/'04_逐根删除评估/review_three_codes.py'
ns={'__file__':str(source)}
exec(source.read_text(encoding='utf-8').split('ledgerpath=')[0],ns)
base,og,rid,freq,readings=(ns[k] for k in ['BASE','og','rid','freq','readings'])
names=['亻','彳','卧人','行'];labels={og(rid(n)):n for n in names}
buckets=defaultdict(lambda:defaultdict(list))
for c,seq in base.items():
    g=labels.get(og(seq[0]))
    if g:
        for s in readings[c]:buckets[s][g].append(c)
for s,gs in buckets.items():
    for cs in gs.values():cs.sort(key=lambda c:(-freq[s,c],c))
out=[];allpairs=set()
for a,b in combinations(names,2):
    rows=[];details=[]
    for s,gs in buckets.items():
        if a not in gs or b not in gs:continue
        ca,cb=gs[a][0],gs[b][0]
        ties=lambda g:[c for c in gs[g] if freq[s,c]==freq[s,gs[g][0]]]
        rows.append({'音节':s,'左代表':ca,'右代表':cb,'左频次':freq[s,ca],'右频次':freq[s,cb],
                     '左并列':ties(a),'右并列':ties(b),'较低频次':min(freq[s,ca],freq[s,cb])})
        for x in gs[a]:
            for y in gs[b]:
                allpairs.add((s,*sorted([x,y])))
                details.append({'音节':s,a:x,b:y})
    rows.sort(key=lambda r:(-r['较低频次'],r['音节']))
    out.append({'分类':a+'—'+b,'代表竞争数':len(rows),'全部新增字对数':len(details),'代表竞争':rows,'全部新增字对':details})
before=ns['pair_sets'](base,readings,ns['grouping'](person=False))[0]
after=ns['pair_sets'](base,readings,ns['grouping'](person=True))[0]
assert allpairs==after-before and len(allpairs)==95
loss=sum(len(gs)-1 for gs in buckets.values() if len(gs)>1)
assert loss==32
notes='此四组合并待定，以下为风险依据，不计入当前累计方案。只比较四种原根组之间新增的三码竞争。同一原根组内部既有重码不单列为新增损失。主表每音、每原根组只取当前已分配字频最高的字作代表；其他字留在完整跨组字对明细，不算新的三简位置。零频或同频并列不代表裁定首选，已保留全部并列字。仍未分配的频次沿用原审计提示；代表选择是当前数据下的估计。'
notes+=' 六类共有34项两两代表竞争，但有yi、yu各三组相遇，因此合并四组实际净减少32个三简位置，不能把34直接当成损失。95对全部新增字对也不等于95个三简位置。'
(HERE/'人旁行跨组分类.json').write_text(json.dumps({'说明':notes,'三码位净减少':loss,'分类':out},ensure_ascii=False,indent=2),encoding='utf-8')
md=['# 人旁、卧人、行：跨组三码竞争','',notes,'','| 原根组组合 | 代表竞争 | 全部新增跨组字对 |','|---|---:|---:|']
for item in out:md.append(f"| {item['分类']} | {item['代表竞争数']} | {item['全部新增字对数']} |")
esc=lambda x:html.escape(str(x))
page='<!doctype html><meta charset="utf-8"><title>人旁行跨组三码分类</title><style>body{font:16px/1.7 Microsoft YaHei,sans-serif;margin:32px;background:#f5f7fa;color:#233548}table{border-collapse:collapse;background:white}th,td{border:1px solid #cdd9e0;padding:8px 16px}p{max-width:1100px}details{margin:16px 0}h2{margin-top:32px}</style><h1>只看不同原根组之间的三码竞争</h1><p>'+esc(notes)+'</p>'
for item in out:
    md+=['',f"## {item['分类']}",'','| 音节 | 左组代表 | 右组代表 |','|---|---|---|']
    page+='<h2>'+esc(item['分类'])+f"：{item['代表竞争数']}项代表竞争</h2><table><tr><th>音节</th><th>左组代表（分音频次）</th><th>右组代表（分音频次）</th></tr>"
    for r in item['代表竞争']:
        left='／'.join(r['左并列']);right='／'.join(r['右并列'])
        md.append(f"| {r['音节']} | {left}（{r['左频次']}） | {right}（{r['右频次']}） |")
        page+='<tr>'+''.join('<td>'+esc(v)+'</td>' for v in [r['音节'],f"{left}（{r['左频次']}）",f"{right}（{r['右频次']}）"] )+'</tr>'
    page+='</table><details><summary>全部新增跨组字对（溯源，不按字对数计算三简损失）</summary>'
    page+='<p>'+esc('；'.join(' '.join(str(v) for v in row.values()) for row in item['全部新增字对']) or '无')+'</p></details>'
(HERE/'人旁行跨组分类.md').write_text('\n'.join(md),encoding='utf-8')
(HERE/'人旁行跨组分类.html').write_text(page,encoding='utf-8')
