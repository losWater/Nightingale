from pathlib import Path
import json,re,collections,hashlib,runpy
P=Path(__file__).resolve().parent;W=P.parent;ROOT=W.parents[1]
source=ROOT/'releases/v0.9.1/99_参考资料/参考/鲸凉鹤1.1手心挂接.txt'
base=Path(json.loads((W/'54_补删鹿旁保留羊南心四起点试跑/二简人工复核/当前裁定基线.json').read_text(encoding='utf-8'))['目录'])/'普通纯单字表.txt'
restore=runpy.run_path(str(P/'restore_fly.py'))['restore']
chars=collections.defaultdict(list);short=set()
for l in base.read_text(encoding='utf-8-sig').splitlines():
 c,k=l.split('\t');chars[k].append(c)
 if len(k)<4:short.add(c)
merges={(r['词'],r['待核码']):r['新码'] for r in json.loads((P/'整词特殊码自动合并.json').read_text(encoding='utf-8'))}
words=collections.defaultdict(list);changes=[];excluded=[];duplicates=[];long=[]
for lineno,l in enumerate(source.read_text(encoding='utf-8-sig').splitlines(),1):
 m=re.fullmatch(r'([a-z]+)=(\d+),(.+)',l)
 if not m:continue
 k,rank,w=m.groups()
 if len(w)<2:continue
 if len(k)<4:excluded.append({'词':w,'码':k,'行':lineno});continue
 original=k
 # Restore known character-bound fly codes only where a complete syllable is present.
 if len(k)==2*len(w):k=''.join(restore(c,k[2*i:2*i+2]) for i,c in enumerate(w))
 elif len(k)==4 and len(w)==3:k=k[:2]+restore(w[-1],k[2:])
 k=merges.get((w,k),k)
 if k!=original:changes.append({'词':w,'原码':original,'新码':k,'行':lineno})
 if len(k)>4:long.append({'词':w,'码':k,'行':lineno})
 if w in words[k]:duplicates.append({'词':w,'码':k,'行':lineno});continue
 words[k].append(w)
merged={};collisions=[]
for k in sorted(set(chars)|set(words)):
 cs=chars[k];ws=words[k]
 if len(k)>=4:
  a=[c for c in cs if c not in short];b=[c for c in cs if c in short];merged[k]=a+ws+b
 else:merged[k]=cs+ws
 if cs and ws:collisions.append({'编码':k,'无简码单字':[c for c in cs if c not in short],'词语':ws,'有简码单字':[c for c in cs if c in short]})
 assert [x for x in merged[k] if len(x)>1]==ws
 assert set(x for x in merged[k] if len(x)==1)==set(cs)
 if len(k)>=4 and ws:
  assert all(merged[k].index(c)>merged[k].index(ws[-1]) for c in cs if c in short)
  assert all(merged[k].index(c)<merged[k].index(ws[0]) for c in cs if c not in short)
(P/'鲸凉鹤非简词_普通码表.txt').write_text(''.join(w+'\t'+k+'\n' for k,ws in sorted(words.items()) for w in ws),encoding='utf-8-sig')
(P/'夜莺2.0字词表_普通格式.txt').write_text(''.join(w+'\t'+k+'\n' for k,ws in merged.items() for w in ws),encoding='utf-8-sig')
(P/'夜莺2.0字词表_手心格式.txt').write_text(''.join(f'{k}={i},{w}\n' for k,ws in merged.items() for i,w in enumerate(ws,1)),encoding='utf-8-sig')
(P/'夜莺2.0字词表_搜狗自定义短语.txt').write_text(''.join(f'{k},{i}={w}\n' for k,ws in merged.items() for i,w in enumerate(ws,1)),encoding='utf-16')
summary={'词来源':str(source),'单字来源':str(base),'单字条目':sum(map(len,chars.values())),'非简词条目':sum(map(len,words.values())),'去除简词条目':len(excluded),'已知飞键还原条目':len(changes),'去重条目':len(duplicates),'长于四码条目':len(long),'字词同码位置':len(collisions),'规则':'保留所有四码及以上原词条（含长码和原词库特殊短语）；无简码单字优先，其次词，最后有任意1至3码的单字全码。同类顺序沿用来源顺序。','飞键限制':'另按WhaleCold_defs.yaml还原20组飞键；逐字映射：百be→bd、几jo→ji、一ei→yi、鹤eh→he、道jf→dc（用户确认作者特设飞键）、之vp→vi、打dw→da、几je→ji、起qe→qi、向xj→xl；合法原读音优先保护。三字四码仅还原末字完整音节，其他缩写不猜测。特殊入口按自动合并清单归并；其余保留不处理，不代表未知飞键已清零。','哈希':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [source,base]}}
for name,obj in [('生成摘要',summary),('飞键还原明细',changes),('去除简词明细',excluded),('去重明细',duplicates),('长码词条',long),('字词同码候选顺序',collisions)]: (P/(name+'.json')).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'说明.txt').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8-sig')
print(json.dumps(summary,ensure_ascii=False,indent=2))
