from pathlib import Path
import json,re,runpy,collections,html,hashlib
P=Path(__file__).resolve().parent;W=P.parent;V=W/'56_鲸凉鹤原词库字词版'
source=W.parents[1]/'releases/v0.9.1/99_参考资料/参考/鲸凉鹤1.1手心挂接.txt'
base=W/'62_无简词字词表导出/夜莺2.0无简词字词表_普通格式.txt'
f=runpy.run_path(str(V/'restore_fly.py'));restore=f['restore'];allowed=f['allowed']
merges={(r['词'],r['待核码']):r['新码'] for r in json.loads((V/'整词特殊码自动合并.json').read_text(encoding='utf-8'))}

initial_fly={'也':('a','y'),'要':('a','y'),'一':('e','y'),'都':('o','d'),'时':('o','u')}
initial_fly_changes=[]
def restore_initial_fly(t,c,origin,record=True):
 old=c
 positions=None
 if re.fullmatch(r'[\u3400-\u9fff]+',t):
  if len(c)==len(t) and len(c) in (2,3):positions=list(range(len(t)))
  elif len(c)==4 and len(t)>=4:positions=[0,1,2,len(t)-1]
 elif t.endswith('儿') and len(c)==len(t)-1 and len(c) in (2,3):positions=list(range(len(c)))
 if positions is not None:
  c=''.join(initial_fly[t[i]][1] if t[i] in initial_fly and key==initial_fly[t[i]][0] else key for key,i in zip(c,positions))
 if c!=old and record:initial_fly_changes.append({'词':t,'原码':old,'新码':c,'来源':origin})
 return c

rows=[l.rsplit('\t',1) for l in base.read_text(encoding='utf-8-sig').splitlines() if l]
original_rows=list(map(tuple,rows))
rows=[(t,restore_initial_fly(t,c,'无简词基表')) for t,c in rows]
# Existing four-character-and-longer entries move behind existing candidates.
existing=collections.defaultdict(list);longbase=collections.defaultdict(list)
for t,c in rows:(longbase if len(t)>=4 else existing)[c].append(t)
add=collections.defaultdict(list);changes=[];special=[];skipped=0
for line,l in enumerate(source.read_text(encoding='utf-8-sig').splitlines(),1):
 m=re.fullmatch(r'([a-z]+)=(\d+),(.+)',l)
 if not m:continue
 c,rank,t=m.groups();rank=int(rank)
 if len(t)<2:continue
 if len(c)==1:skipped+=1;continue
 if not (len(c) in (2,3) or len(t)>=4):continue
 old=c
 if len(c)==len(t)*2:c=''.join(restore(ch,c[2*i:2*i+2]) for i,ch in enumerate(t))
 elif len(c)==3 and len(t)==2:
  candidate=restore(t[0],c[:2])
  if candidate in allowed[t[0]]:c=candidate+c[2:]
  else:special.append({'词':t,'码':c,'说明':'不能确认前两码为首字完整音节，保留'})
 # Initial-letter abbreviations are not full double-pinyin syllables.
 elif len(c)<=3:special.append({'词':t,'码':c,'说明':'缩写或特殊简词，保留原码，不按两码音节盲改'})
 c=merges.get((t,c),c)
 c=restore_initial_fly(t,c,'鲸凉鹤源词')
 r={'词':t,'原码':old,'新码':c,'原序':rank,'原行':line}
 add[c].append(r)
 if old!=c:changes.append(r)
fixed_initial_fly={(r['词'],r['原码']) for r in initial_fly_changes}
special=[r for r in special if (r['词'],r['码']) not in fixed_initial_fly]
combined={};collisions=[];new=0
for c in sorted(set(existing)|set(longbase)|set(add)):
 current=list(existing[c]);seen=set(current)
 groups=collections.defaultdict(list)
 for r in add[c]:groups[r['原码']].append(r)
 for g in groups.values():g.sort(key=lambda r:(r['原序'],r['原行']))
 # Keep each source group intact; use first source appearance as provisional group order.
 order=sorted(groups,key=lambda k:min(r['原行'] for r in groups[k]))
 if len(order)>1:collisions.append({'码':c,'说明':'组间暂按源文件首次出现顺序，各组内部按原候选序；未视为跨组词频排名','组':[{'原码':k,'词':[r['词'] for r in groups[k]]} for k in order]})
 for k in order:
  for r in groups[k]:
   if r['词'] not in seen:current.append(r['词']);seen.add(r['词'])
 for t in longbase[c]:
  if t not in seen:current.append(t);seen.add(t)
 combined[c]=current
# User-approved conversion of one-key words to initial abbreviations.
initial_map=json.loads((P/'一简词转声母配置.json').read_text(encoding='utf-8'))
one_words=[]
for l in source.read_text(encoding='utf-8-sig').splitlines():
 m=re.fullmatch(r'([a-z])=(\d+),(.+)',l)
 if m and len(m[3])>1:one_words.append((m[3],m[1],int(m[2])))
assert len(one_words)==50 and all(t in initial_map for t,_,_ in one_words)
initial_audit=[]
for t,old,rank in one_words+[('什么','',0)]:
 for c in initial_map[t]:
  before=list(combined.get(c,[]));added=t not in before
  if added:combined.setdefault(c,[]).append(t)
  initial_audit.append({'词':t,'原一简':old,'原候选位':rank,'新码':c,'本次新增':added,'当前候选位':combined[c].index(t)+1,'此前候选':before})
(P/'一简词转声母结果.json').write_text(json.dumps(initial_audit,ensure_ascii=False,indent=2),encoding='utf-8')
combined=dict(sorted(combined.items()))
# Apply user-approved word ordering within existing word slots only.
judgement_path=P/'简词人工裁定.json'
if judgement_path.exists():
 preferences=collections.defaultdict(list)
 for oldcode,words in json.loads(judgement_path.read_text(encoding='utf-8')).items():
  for t in words:
   c=restore_initial_fly(t,oldcode,'人工裁定迁移',False)
   if t not in preferences[c]:preferences[c].append(t)
 for c,preferred in preferences.items():
  if c not in combined:continue
  current=combined[c];available={t for t in current if len(t)>1}
  words=[t for t in preferred if t in available]
  words += [t for t in current if len(t)>1 and t not in words]
  assert len(words)==len(available)
  queue=iter(words);combined[c]=[next(queue) if len(t)>1 else t for t in current]
explicit=runpy.run_path(str(P/'apply_explicit_candidates.py'))['apply']
normalize=lambda t,c:restore_initial_fly(t,c,'人工指定迁移',False)
combined=explicit(combined,short_only=True,normalize=normalize)
cap=runpy.run_path(str(P/'cap_short_words.py'))['apply_cap']
combined,cap_summary,removed_pairs=cap(combined,allowed,restore,source)
combined,full_summary=runpy.run_path(str(P/'full_code_order.py'))['reorder'](combined,source,restore,merges)
combined=explicit(combined,normalize=normalize)
combined=dict(sorted(combined.items()))
outrows=[(t,c) for c,ts in combined.items() for t in ts]
oldset=set(map(tuple,rows));newset=set(outrows)
assert oldset-newset <= removed_pairs
assert {(t,c) for t,c in outrows if len(t)==1}=={(t,c) for t,c in rows if len(t)==1}
assert len(outrows)==len(newset)
# Full-code candidate ordering is validated by full_code_order.py.
for name,front in [('夜莺2.0含简词字词表_普通格式.txt',False),('夜莺2.0含简词字词表_码前格式.txt',True)]:
 (P/name).write_text(''.join((c+'\t'+t if front else t+'\t'+c)+'\n' for t,c in outrows),encoding='utf-8-sig')
summary={'简词字位飞键还原记录':len(initial_fly_changes),'总条目':len(outrows),'新增词码':len(newset-oldset),'原有四字及以上词码':sum(map(len,longbase.values())),'本批确认还原飞键条目':len(changes),'去飞键合流码位':len(collisions),'转为声母简词的原一简词':skipped,'本批补充词码':sum(r['本次新增'] for r in initial_audit),'保留原码的简词条目':len(special),'规则':'二简词、三简词、四字及以上词追加在既有候选后；原库组内按显式候选序；飞键合流组单列，暂按源文件组首次出现次序排列；原一简词改为逐字声母简码，追加在已有候选后；为什么同时保留wum/wsm，什么同时保留um/sm。','飞键边界':'按简词实际字位还原一e→y、也a→y、要a→y、都o→d、时o→u；含二三简、四字以上首三末一及儿化省尾。其余特殊缩写保留原码。','验证':'字位飞键语义校验；单字编码完全一致；原有全码保留；无重复词码。','来源':{str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in [source,base]}}
summary['人工指定码位']=json.loads((P/'码位人工指定.json').read_text(encoding='utf-8'))
summary['全码排序']=full_summary
summary['三选裁剪']=cap_summary
summary['规则']='原一简词转声母，人工简词顺序优先；为什么wum/wsm及什么um/sm保留。'+cap_summary['规则']+full_summary['规则']
summary['验证']='单字码位与当前基线一致；原有全码保留；人工指定码位优先（含qtxb确信在碏前）；其余遵循既有让位及三选规则；所有撤码可追溯；无重复词码。'
for n,obj in [('生成摘要',summary),('去飞键合流组',collisions),('简词字位飞键还原',initial_fly_changes),('本批飞键还原',changes),('保留原码简词',special)]:
 (P/(n+'.json')).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
esc=html.escape
page='<meta charset="utf-8"><title>加入鲸凉鹤简词</title><style>body{font:17px/1.7 Microsoft YaHei;margin:30px}td,th{border:1px solid #ccd;padding:10px}table{border-collapse:collapse}</style><h1>加入鲸凉鹤简词</h1><pre>'+esc(json.dumps(summary,ensure_ascii=False,indent=2))+'</pre><h2>去飞键合流组（组间顺序暂定）</h2><table><tr><th>新码</th><th>各原码组</th></tr>'
for r in collisions:page+='<tr><td>'+esc(r['码'])+'</td><td>'+'<br>'.join(esc(g['原码']+'：'+'、'.join(g['词'])) for g in r['组'])+'</td></tr>'
page+='</table>'
(P/'生成说明与合流组.html').write_text(page,encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
