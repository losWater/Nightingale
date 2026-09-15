from pathlib import Path
import json,runpy,hashlib
from collections import Counter
O=Path(__file__).resolve().parent
m=runpy.run_path(str(O/'auto_review.py'));dc=m['dc']
source=O/'二字词60000_高频复核后.jsonl'
rows=[json.loads(x) for x in source.read_text(encoding='utf-8').splitlines()]
accepted={'沿用通过','自动确定主读','单音字组合通过','高频逐项核对候选'}
records=[];stats=Counter()
for r in rows:
 if r['处理分类'] in accepted:continue
 w=r['词'];ev=r['读音证据'];j=ev.get('鲸凉鹤',[])
 if r['二字词排名']<=10000:status='沿用高频待定'
 elif not j:status='鲸凉鹤缺少可还原整词读音'
 elif len(j)>1:status='鲸凉鹤多个读音'
 else:
  py=j[0];code=''.join(dc(x) for x in py.split())
  disagreements={k:v for k,v in ev.items() if k!='鲸凉鹤' and ((k=='墨奇双拼' and any(x!=code for x in v)) or (k!='墨奇双拼' and any(x!=py for x in v)))}
  if disagreements:status='与其他来源有分歧'
  else:
   assert m['valid'](w,py)
   status='鲸凉鹤唯一读音补全候选'
   r.update(处理分类=status,主读音=py,主读双拼=code,处理依据='按用户指定优先参考鲸凉鹤；去已知飞键后唯一读音，现有整词证据无分歧。仅补全候选，未逐词核实。')
 stats[status]+=1
 records.append({'词':w,'排名':r['二字词排名'],'结果':status,'鲸凉鹤':j,'全部证据':ev})
for name,data in [('二字词60000_鲸凉鹤补全后.jsonl',rows),('鲸凉鹤补全候选.jsonl',[r for r in rows if r['处理分类']=='鲸凉鹤唯一读音补全候选'])]:
 (O/name).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in data),encoding='utf-8')
(O/'鲸凉鹤补全审计.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
assert sum(stats.values())==2964
assert len(rows)==60000 and len({r['词'] for r in rows})==60000
n=stats['鲸凉鹤唯一读音补全候选']
summary={'分类':dict(stats),'新增补全候选':n,'此前读音通过候选':57036,'补全后有候选读音':57036+n,'剩余未补全':2964-n,'输入SHA256':hashlib.sha256(source.read_bytes()).hexdigest()}
(O/'鲸凉鹤补全摘要.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 鲸凉鹤读音补全第二批','',f'新增{n}条唯一读音补全候选。此前57036条读音候选保留，本轮补全后共{57036+n}条；剩余{2964-n}条。','', '本轮新增项是用户指定参考来源的补全候选，不等同于逐词核实通过。不改正式发布数据，不分配多音词频率。前10000词的33条待定保持原状。','', '|分类|数量|','|---|---:|']
lines += [f'|{k}|{v}|' for k,v in stats.items()]
lines += ['', '仅接收鲸凉鹤去已知飞键后唯一读音、且其他现有来源无不同读音或编码的项。未知飞键没有猜测还原。','', '完整候选：二字词60000_鲸凉鹤补全后.jsonl；逐项依据：鲸凉鹤补全审计.json。']
(O/'鲸凉鹤补全说明.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
