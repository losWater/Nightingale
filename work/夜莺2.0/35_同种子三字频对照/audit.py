from pathlib import Path
import json,yaml,hashlib,re
P=Path(__file__).resolve().parent;W=P.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
strip=lambda es:sorted([json.dumps({k:v for k,v in e.items() if k!='频率'},ensure_ascii=False,sort_keys=True) for e in es])
inputs={label:yaml.safe_load((P/(label+'_elements.yaml')).read_text(encoding='utf-8')) for label in ['老表','新表','盒子表']}
assert strip(inputs['老表'])==strip(inputs['新表'])==strip(inputs['盒子表'])
cf=[(P/label/'五万步/run.json').read_bytes() for label in inputs];assert cf[0]==cf[1]==cf[2]
checks={}
for label in inputs:
 log=(P/label/'五万步/stdout.log').read_text(encoding='utf-8');assert re.search(r'已执行 50000 步',log)
 err=(P/label/'五万步/stderr.log').read_text(encoding='utf-8');d=float(re.search(r'TRIAL_CACHE_DELTA ([^\s]+)',err)[1]);assert abs(d)<1e-7
 checks[label]={'steps':50000,'缓存核验差异':d,'复核':read(P/label/'result.json')['复核'],'单字表SHA256':hashlib.sha256((P/(label+'_五万步单字表.txt')).read_bytes()).hexdigest()}
resources=[json.loads(l) for l in (P/'resources.jsonl').read_text().splitlines()]
base=read(W/'32_多来源字频重建/分音字频_试验.json');box={l.split('\t')[0] for l in (W/'30_形码盒子1.0复测/默认字频.txt').read_text().splitlines()};fallback={a['字'] for a in base if a['字'] in box and a['整字频率']==0}
v={'去频率后输入逐项一致':True,'起点与参数文件逐字节一致':True,'短跑重复性':read(P/'随机重复性核验.json'),'三臂核验':checks,'最低可用内存GiB':min(r['availableGiB'] for r in resources),'资源采样跨度秒':resources[-1]['time']-resources[0]['time'],'盒子有频新表无比例的字数':len(fallback),'这些字':''.join(sorted(fallback)),'回退规则':'这些字在方案读音集合内均分（单读音则全配）；不宣称真实读音比例'}
(P/'最终核验.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(v,ensure_ascii=False))
r=read(P/'三字频交叉测评.json')
for ev in ['盒子表','新表','老表']:
 print(ev)
 for a in r:
  if a['测评字频']==ev and a['阶段']=='五万步':print(a['训练字频'],[round(s['键均当量'],6) for s in a['分档']])
