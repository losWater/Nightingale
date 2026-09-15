from pathlib import Path
import collections,json,re,html,csv
P=Path(__file__).resolve().parent

def apply_cap(combined,allowed,restore,source):
 config=json.loads((P/'三选保留配置.json').read_text(encoding='utf-8'))
 before={c:list(ts) for c,ts in combined.items()}
 full=collections.defaultdict(set)
 for c,ts in before.items():
  if len(c)>=4:
   for t in ts:full[t].add(c)
 refs=collections.defaultdict(lambda:collections.defaultdict(set))
 paths=[source,Path('D:/nightingale/releases/v1.0/01_正式码表/夜莺1.0字词表.txt'),P.parents[2]/'releases/v0.9.1/99_参考资料/参考/简单鹤V9.3.0纯词库 (1).txt']
 for path in paths:
  for line in path.read_text(encoding='utf-8-sig').splitlines():
   m=re.fullmatch(r'([a-z]{4})=\d+,(.{2})',line)
   if m:c,t=m.groups()
   else:
    parts=line.split('\t')
    if len(parts)!=2:continue
    t,c=parts
   if len(t)!=2 or not re.fullmatch('[a-z]{4}',c):continue
   c=''.join(restore(ch,c[i*2:i*2+2]) for i,ch in enumerate(t))
   if all(c[i*2:i*2+2] in allowed[ch] for i,ch in enumerate(t)):
    refs[t][c].add(path.name)
 removed=[];pending=[];added=[];groups=[]
 for c,ts in before.items():
  if len(c) not in (2,3) or c in config['整组保留']:continue
  chars=[t for t in ts if len(t)==1];words=[t for t in ts if len(t)>1]
  budget=max(0,3-len(chars))
  protected=set(config['指定词保留'].get(c,[]))&set(words)
  assert len(protected)<=budget,(c,protected)
  keep=set(protected)
  for t in words:
   if len(keep)<budget:keep.add(t)
  deferred=set()
  for t in words:
   if t in keep:continue
   if len(t)==2 and not full[t]:
    candidates=refs[t]
    code=None;evidence=[]
    if len(candidates)==1:code=next(iter(candidates));evidence=sorted(candidates[code])
    elif not candidates and all(len(allowed[ch])==1 for ch in t):
     code=''.join(next(iter(allowed[ch])) for ch in t);evidence=['当前字音基准中两字各仅一个音码']
    if code:
     combined.setdefault(code,[]).append(t);full[t].add(code)
     added.append({'词':t,'全码':code,'依据':evidence})
    else:
     deferred.add(t);pending.append({'词':t,'简码':c,'原因':'整词参考读音冲突' if candidates else '缺少可确认的整词读音','参考全码':sorted(candidates),'逐字音码':[sorted(allowed[ch]) for ch in t]});continue
   removed.append({'词':t,'简码':c,'已有全码':sorted(full[t]),'处理':'二字词保留全码' if len(t)==2 else '三字及以上不补全码'})
  combined[c]=[t for t in ts if len(t)==1 or t in keep or t in deferred]
  if combined[c]!=ts or deferred:groups.append({'码':c,'原候选':ts,'现候选':combined[c],'暂缓':list(deferred)})
 oldpairs={(t,c) for c,ts in before.items() for t in ts};newpairs={(t,c) for c,ts in combined.items() for t in ts}
 assert oldpairs-newpairs=={(r['词'],r['简码']) for r in removed}
 assert newpairs-oldpairs=={(r['词'],r['全码']) for r in added}
 assert {(t,c) for t,c in oldpairs if len(t)==1 or len(c)>=4}<=newpairs
 for r in removed:
  if len(r['词'])==2:assert full[r['词']]
 for c,ts in combined.items():
  assert len(ts)==len(set(ts)),c
  if len(c) in (2,3) and c not in config['整组保留']:
   assert len(ts)<=3 or any(r['简码']==c for r in pending),c
 stats={'撤下超额简码':len(removed),'补全码二字词':len(added),'暂缓二字词码':len(pending),'撤下三字及以上简码':sum(len(r['词'])>2 for r in removed),'调整码位':len(groups),'规则':'默认单字与简词合计三选；lj整组保留；指定绑定优先占词位；二字词先保全码，不确定暂缓；三字以上不补全码。'}
 audit={'摘要':stats,'补全码':added,'撤简码':removed,'暂缓':pending,'码位变化':groups,'保留配置':config}
 (P/'三选裁剪结果.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
 esc=html.escape
 page='<meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>简词三选裁剪结果</title><style>body{background:#f2f1eb;color:#243a3a;font:16px/1.7 Microsoft YaHei;margin:24px}table{border-collapse:collapse;width:100%}td,th{padding:10px;border:1px solid #d7ddd1;text-align:left}th{background:#e7ece4}</style><h1>简词三选裁剪结果</h1><pre>'+esc(json.dumps(stats,ensure_ascii=False,indent=2))+'</pre><p>暂缓项仍保留原简码，可能暂时超过三选。单字与原有全码均保留。</p>'
 for title,entries in [('码位变化',groups),('补全码',added),('暂缓',pending)]:
  page+='<h2>'+title+'</h2>'
  if not entries:continue
  fields=list(entries[0]);page+='<table><tr>'+''.join('<th>'+esc(k)+'</th>' for k in fields)+'</tr>'
  for row in entries:page+='<tr>'+''.join('<td>'+esc('、'.join(map(str,row[k])) if isinstance(row[k],list) else str(row[k]))+'</td>' for k in fields)+'</tr>'
  page+='</table>'
 (P/'三选裁剪结果.html').write_text(page,encoding='utf-8')
 return combined,stats,{(r['词'],r['简码']) for r in removed}
