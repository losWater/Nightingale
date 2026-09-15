from pathlib import Path
import json,collections,hashlib
P=Path(__file__).resolve().parent;W=P.parents[1]
b=Path(json.loads((W/'54_补删鹿旁保留羊南心四起点试跑/二简人工复核/当前裁定基线.json').read_text(encoding='utf-8'))['目录'])/'普通纯单字表.txt'
pairs=dict(x.split(':') for x in 'cs:cl dc:dl gr:gp gv:gi jm:jz lp:lf mj:mr mu:mx nj:nz pi:px pk:px po:ps qx:qo tv:tl uj:us vg:vk xq:xo yj:yf yu:yg zs:zl'.split())
raw=b.read_bytes();old=[tuple(l.split('\t')) for l in raw.decode('utf-8-sig').splitlines()];dest=collections.defaultdict(list);changes=[];sources=collections.defaultdict(set)
for moved in [True,False]:
 for c,k in old:
  nk=pairs.get(k[:2],k[:2])+k[2:] if len(k)>=2 else k
  if (nk!=k)!=moved:continue
  dest[nk].append(c);sources[nk].add(k)
  if moved:changes.append({'字':c,'原码':k,'实验码':nk})
coll=[{'实验码':k,'原码来源':sorted(sources[k]),'候选':v} for k,v in dest.items() if len(sources[k])>1]
assert sum(map(len,dest.values()))==len(old)
assert {c for c,k in old}=={c for cs in dest.values() for c in cs}
for c,k in old:
 nk=pairs.get(k[:2],k[:2])+k[2:] if len(k)>=2 else k
 assert c in dest[nk] and (len(k)<2 or nk[2:]==k[2:])
(P/'普通单字表_pi飞px实验.txt').write_text(''.join(c+'\t'+k+'\n' for k,cs in sorted(dest.items()) for c in cs),encoding='utf-8-sig')
(P/'普通单字表_原版对照.txt').write_bytes(raw)
meta={'仅实验':True,'来源':str(b),'来源SHA256':hashlib.sha256(raw).hexdigest(),'飞键规则':pairs,'条目数':len(old),'汉字数':len({c for c,k in old}),'变化条目':len(changes),'涉及字数':len({r['字'] for r in changes}),'新增合码':coll,'规则':'整体替换二三四码音部，原音码不作为兼容码保留；一简、形部不变。飞入字优先，原占位字退后；pi与pk均飞px，两组依原表出现顺序合并；无重排简码，无退火，不实装。'}
for name,data in [('实验说明',meta),('飞键变动明细',changes)]: (P/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
assert b.read_bytes()==raw
print(json.dumps(meta,ensure_ascii=False))
