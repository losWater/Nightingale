from pathlib import Path
import json,re,collections,shutil,runpy,contextlib,io,zipfile,hashlib,html
W=Path(__file__).resolve().parent.parent;P=Path(__file__).resolve().parent;B=P/'实装前备份';B.mkdir(exist_ok=True)
T=W/'54_补删鹿旁保留羊南心四起点试跑';U=W/'65_群友离线工具包';V=W/'64_加入鲸凉鹤简词'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def backup(p):
 if p.exists():
  q=B/p.relative_to(W);q.parent.mkdir(parents=True,exist_ok=True)
  if not q.exists():shutil.copy2(p,q)
def write(p,s,enc='utf-8'):
 backup(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding=enc)
def jout(p,x):write(p,json.dumps(x,ensure_ascii=False,indent=2))
def get(s,name):
 m=re.search(r'\b(?:const|let) '+re.escape(name)+r'\s*=\s*',s);assert m,name
 obj,n=json.JSONDecoder().raw_decode(s[m.end():]);return obj,m.end(),m.end()+n
def put(s,name,obj):
 _,a,b=get(s,name);return s[:a]+json.dumps(obj,ensure_ascii=False).replace('<','\\u003c')+s[b:]
conf=read(P/'裁定配置.json');targets=conf['码位安排'];ptr=T/'二简人工复核/当前裁定基线.json';previous=read(ptr);old=Path(previous['目录']);new=old.parent/'第二十一批_简码任选项定稿'
assert not new.exists(),'Already installed'
groups=collections.defaultdict(list)
for line in (old/'普通纯单字表.txt').read_text(encoding='utf-8-sig').splitlines():
 c,k=line.split('\t');groups[k].append(c)
oldpairs={(c,k) for k,chars in groups.items() for c in chars};oldgroups=dict((k,list(v)) for k,v in groups.items());audit=[]
for k,terms in targets.items():
 chars=[t for t in terms if len(t)==1]
 assert all(any(c==x for x,code in oldpairs) for c in chars),(k,chars)
 before=list(groups[k])
 if len(k)<4:groups[k]=chars
 else:
  assert set(chars)<=set(before),(k,chars,before)
  groups[k]=chars+[c for c in before if c not in chars]
 audit.append({'码':k,'指定候选':terms,'原单字':before,'新单字':groups[k]})
newpairs={(c,k) for k,chars in groups.items() for c in chars}
assert {r for r in oldpairs if len(r[1])==4}=={r for r in newpairs if len(r[1])==4}
assert {c for c,k in oldpairs}=={c for c,k in newpairs}
for line in conf['待议原文']:
 for k in re.findall(r'(?<![a-z])[a-z]{1,4}(?![a-z])',line.split('    ')[0]):assert groups[k]==oldgroups.get(k,[]),k
shutil.copytree(old,new)
normal=''.join(c+'\t'+k+'\n' for k in sorted(groups) for c in groups[k]);write(new/'普通纯单字表.txt',normal,'utf-8-sig')
jout(new/'此前基线指针.json',previous);jout(new/'裁定记录.json',conf);special=read(new/'无理码.json');special.update({'ufd':'深','qmd':'浅','whw':'望'});jout(new/'无理码.json',special)
jout(new/'手工简码安排.json',targets)
# Update non-abbreviated word exports: preserve every word-code binding.
f=W/'62_无简词字词表导出/夜莺2.0无简词字词表_普通格式.txt';pairs=[tuple(l.rsplit('\t',1)) for l in f.read_text(encoding='utf-8-sig').splitlines() if l];allgroups=collections.defaultdict(list)
for c,k in pairs:
 if len(c)>1:allgroups[k].append(c)
for k,chars in groups.items():allgroups[k]=chars+allgroups[k]
out=[(c,k) for k in sorted(allgroups) for c in allgroups[k]]
assert {x for x in out if len(x[0])>1}=={x for x in pairs if len(x[0])>1}
texts={'普通格式':''.join(c+'\t'+k+'\n' for c,k in out),'码前格式':''.join(k+'\t'+c+'\n' for c,k in out),'手心格式':''.join(f'{k}={i},{c}\n' for k in sorted(allgroups) for i,c in enumerate(allgroups[k],1)),'搜狗':''.join(f'{k},{i}={c}\n' for k in sorted(allgroups) for i,c in enumerate(allgroups[k],1))}
for suffix,s in texts.items():write(f.parent/('夜莺2.0无简词字词表_'+suffix+'.txt'),s,'utf-16' if suffix=='搜狗' else 'utf-8-sig')
write(new/'无简词字词表.txt',texts['手心格式'],'utf-8-sig');jout(ptr,{'目录':str(new),'记录':str(new/'裁定记录.json'),'根表':str(new/'当前完整根表.json')})
# Persist explicit candidate ordering after ordinary policy; explicit lists are narrow exceptions.
alltargets=read(V/'码位人工指定.json');alltargets.update(targets);jout(V/'码位人工指定.json',alltargets)
for folder in [V,W/'59_单字当量排行']:
 for f in folder.iterdir():
  if f.is_file() and f.suffix in ['.json','.txt','.html']:backup(f)
with contextlib.redirect_stdout(io.StringIO()):runpy.run_path(str(V/'build.py'),run_name='__main__')
# Sync lookup data only. Practice, root chart, roots and progress code remain byte-for-byte unchanged.
f58=W/'58_拆分查询/夜莺2.0拆分查询.html';s=f58.read_text(encoding='utf-8-sig');D,_,_=get(s,'D')
for r in D.values():r['编码']=[]
for k,chars in groups.items():
 for i,c in enumerate(chars,1):D[c]['编码'].append({'码':k,'位':i,'同码':chars})
for r in D.values():r['编码'].sort(key=lambda e:(len(e['码']),e['码']))
write(f58,put(s,'D',D))
main=U/'夜莺2.0随身工具_单文件.html';shell=main.read_text(encoding='utf-8-sig');views,_,_=get(shell,'views');practicehash=hashlib.sha256(views['practice'].encode()).hexdigest()
for key,name in [('query','拆分查询.html'),('components','部件反查.html')]:
 views[key]=put(views[key],'D',D);write(U/'夜莺2.0离线工具包'/name,views[key])
shell=put(shell,'views',views);write(main,shell);write(U/'夜莺啾啾工具箱.html',shell)
with contextlib.redirect_stdout(io.StringIO()):runpy.run_path(str(W/'59_单字当量排行/build.py'),run_name='__main__')
changed=sorted({c for c,k in oldpairs^newpairs},key=lambda c:D[c]['排名'])
report={'直接实装条数':len(conf['实装原文']),'待议条数':len(conf['待议原文']),'涉及码位':len(targets),'简码变化字数':len(changed),'变化字':changed,'撤简码':sorted(oldpairs-newpairs),'新增简码':sorted(newpairs-oldpairs),'全码集合':'完全保留','练习代码SHA256':practicehash,'待议':conf['待议原文'],'逐码安排':audit}
jout(P/'实装报告.json',report);jout(new/'实装核验.json',report)
page='<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>简码建议实装与待议</title><style>body{font:17px/1.7 system-ui;background:#f2f1eb;color:#243a3a;margin:24px}table{border-collapse:collapse}td,th{border:1px solid #d7ddd1;padding:8px}code{color:#366d62}</style><h1>任选项已全部定稿</h1><p>5条修改、5条保持原样，任选项全部定稿。ud首选说道，次选说道：“。</p><h2>无待议项</h2><ul>'+''.join('<li>'+html.escape(x)+'</li>' for x in conf['待议原文'])+'</ul><h2>实装码位</h2><table><tr><th>码</th><th>原单字</th><th>指定候选（按序）</th></tr>'+''.join('<tr><td>'+r['码']+'</td><td>'+html.escape('、'.join(r['原单字']))+'</td><td>'+html.escape('、'.join(r['指定候选']))+'</td></tr>' for r in audit)+'</table>'
write(P/'实装与待议.html',page)
print(json.dumps({k:v for k,v in report.items() if k in ['直接实装条数','待议条数','涉及码位','简码变化字数','变化字']},ensure_ascii=False))
