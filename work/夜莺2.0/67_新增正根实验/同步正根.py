from pathlib import Path
import json,re,collections,shutil,runpy,contextlib,io,zipfile
W=Path('E:/夜莺2.0/work/夜莺2.0');P=W/'67_新增正根实验';T=W/'54_补删鹿旁保留羊南心四起点试跑';U=W/'65_群友离线工具包';O=U/'夜莺2.0离线工具包';B=P/'正式同步前备份';B.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,s,encoding='utf-8'):
 p=Path(p)
 if p.exists():
  q=B/p.relative_to(W);q.parent.mkdir(parents=True,exist_ok=True)
  if not q.exists():shutil.copy2(p,q)
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding=encoding)
def jout(p,x):write(p,json.dumps(x,ensure_ascii=False,indent=2))
def get(s,name):
 m=re.search(r'\b(?:const|let) '+re.escape(name)+r'\s*=\s*',s);assert m,name
 obj,n=json.JSONDecoder().raw_decode(s[m.end():]);return obj,m.end(),m.end()+n
def put(s,name,obj):
 _,a,b=get(s,name);return s[:a]+json.dumps(obj,ensure_ascii=False).replace('<','\\u003c')+s[b:]
D=read(P/'正归S_查询数据.json');changes={('正','vgps'):'vgss',('政','vgp'):'vgs',('政','vgpq'):'vgsq',('焉','yjpp'):'yjsp',('鄢','yjpy'):'yjsy',('妍','yjs'):None}
ptr=T/'二简人工复核/当前裁定基线.json';old=read(ptr);base=Path(old['目录']);new=base.parent/'第十九批_正归止与焉三简'
assert not new.exists(),'already published'
shutil.copytree(base,new)
short=(P/'正归S_普通单字表.txt').read_text(encoding='utf-8-sig');write(new/'普通纯单字表.txt',short,'utf-8-sig')
root_table=read(T/'frozen/当前完整根表.json')
for r in root_table['根组']:
 if '止' in r['根形']:r['根形'].append('正');r['根形ID'].append('正')
root_table['条目数']=404;root_table['说明']='当前裁定：正新增归止S，130根组、404根形；练习正单独追加末尾。'
jout(new/'当前完整根表.json',root_table);jout(new/'新增根形.json',{'正':{'键':'s','归并':'止','拆分替换':['一','止'],'练习顺序':'末尾'}})
jout(new/'此前基线指针.json',old);jout(new/'裁定记录.json',{'说明':'正归止S；政三简vgs；焉三简yjs，妍只留yjsm；女不移动。','前基线':str(base),'根表':str(new/'当前完整根表.json')})
f=W/'62_无简词字词表导出/夜莺2.0无简词字词表_普通格式.txt';orig=[tuple(l.rsplit('\t',1)) for l in f.read_text(encoding='utf-8-sig').splitlines() if l];g=collections.defaultdict(list)
for c,k in orig:
 if (c,k) not in changes:g[k].append(c)
for (c,k),nk in changes.items():
 if nk:
  items=g[nk];idx=next((i for i,x in enumerate(items) if len(x)>1 or D[x]['排名']>D[c]['排名']),len(items));items.insert(idx,c)
g['yjs'].insert(0,'焉')
pairs=[(c,k) for k in sorted(g) for c in g[k]]
assert {(c,k) for c,k in pairs if len(c)==1}=={tuple(l.split('\t')) for l in short.splitlines()}
assert {(c,k) for c,k in pairs if len(c)>1}=={(c,k) for c,k in orig if len(c)>1}
normal=''.join(c+'\t'+k+'\n' for c,k in pairs);front=''.join(k+'\t'+c+'\n' for c,k in pairs);hand=''.join(f'{k}={i},{c}\n' for k in sorted(g) for i,c in enumerate(g[k],1));sogou=''.join(f'{k},{i}={c}\n' for k in sorted(g) for i,c in enumerate(g[k],1))
for suffix,text,enc in [('普通格式',normal,'utf-8-sig'),('码前格式',front,'utf-8-sig'),('手心格式',hand,'utf-8-sig'),('搜狗',sogou,'utf-16')]:write(f.parent/('夜莺2.0无简词字词表_'+suffix+'.txt'),text,enc)
write(new/'无简词字词表.txt',hand,'utf-8-sig');jout(ptr,{'目录':str(new),'记录':str(new/'裁定记录.json'),'根表':str(new/'当前完整根表.json')})
a=W/'55_拆分继承核验/全部拆分对照.json';rows=read(a);ids=read(a.parent/'当前完整拆分_根ID.json');affected=[]
for r in rows:
 c=r['字']
 if r['新拆']!=D[c]['新拆']:
  affected.append(c);oldids=r['新根ID'];out=[];i=0
  while i<len(oldids):
   if i+1<len(oldids) and oldids[i] in ['1','一'] and oldids[i+1]=='止':out.append('正');i+=2
   else:out.append(oldids[i]);i+=1
  r['新拆']=D[c]['新拆'];r['新根ID']=out;r['人工校对']=True;r['核验依据']='第十九批裁定：一＋止合并为正，归S';ids[c]=out
assert len(affected)==18
jout(a,rows);jout(a.parent/'当前完整拆分_根ID.json',ids)
splitrows=[[c,r['新拆'],r['根'][0]['根'],r['根'][-1]['根']] for c,r in D.items()]
splittext='汉字\t完整拆分\t首根\t末根\n'+''.join('\t'.join(x)+'\n' for x in splitrows)
write(a.parent/'当前完整拆分表.txt',splittext,'utf-8-sig')
main=U/'夜莺2.0随身工具_单文件.html';shell=main.read_text(encoding='utf-8-sig');views,_,_=get(shell,'views');oldpractice=views['practice'];write(P/'迁移测试_旧练习.js',re.search(r'<script>([\s\S]*)</script>',oldpractice)[1])
root={'根':'正','键':'s','组':'走／止／足／定字底'}
for k in ['query','components']:
 v=put(views[k],'D',D);rs,_,_=get(v,'ROOTS');rs.append(root);views[k]=put(v,'ROOTS',rs)
f58=W/'58_拆分查询/夜莺2.0拆分查询.html';v=f58.read_text(encoding='utf-8-sig');v=put(v,'D',D)
if re.search(r'const ROOTS\s*=',v):rs,_,_=get(v,'ROOTS');rs.append(root);v=put(v,'ROOTS',rs)
write(f58,v)
v=views['practice'];roots,_,_=get(v,'roots');roots.append({**root,'例字':'政、整、焉、证'});v=put(v,'roots',roots)
v=v.replace('Object.values(roots.reduce','Object.values(roots.filter(x=>x.根!=="正").reduce')
needle="document.querySelector('#kind').options[0]"
v=v.replace(needle,'grouped.push({根:"正",键:"s",原组:"走／止／足／定字底",归并提示:"止",成员:["正"],例字:"政、整、焉、证"});\n'+needle,1)
v=v.replace('const decks={group:grouped,all:roots};',"document.querySelector('#kind').options[1].textContent='全部根形练习（'+roots.length+'根）';\nconst decks={group:grouped,all:roots};")
examples={}
for rr in roots:
 name=rr['根'];candidates=[]
 for c,r in sorted(D.items(),key=lambda t:t[1]['排名']):
  rs=r['根'];first=rs[0]['根']==name;last=rs[-1]['根']==name
  if first or last:candidates.append({'字':c,'位置':'首末' if first and last else '首根' if first else '末根','拆分':r['新拆']})
 examples[name]={}
 for n in [1,2,4]:
  chosen=[]
  for pos in (['首根','末根']*(n//2) if n>1 else ['首根']):
   x=next((x for x in candidates if x not in chosen and x['位置']==pos),None)
   if x:chosen.append(x)
  for x in candidates:
   if len(chosen)>=n:break
   if x not in chosen:chosen.append(x)
  examples[name][str(n)]=chosen
v=put(v,'rootExamples',examples);jout(U/'练习逐根例字.json',examples)
upgrade=r'''function upgradeAppend(s,k){
 if(valid(s,k))return s;
 try{
  const previous=JSON.parse(s.signature),current=decks[k].map(x=>[x.根,x.键]),n=previous.length;
  if(!Array.isArray(previous)||n!==current.length-1||current[n][0]!=="正"||JSON.stringify(previous)!==JSON.stringify(current.slice(0,n)))return s;
  if(!Array.isArray(s.records)||s.records.length!==n||!s.records.every(r=>Array.isArray(r)&&r.length===2&&Number.isInteger(r[0])&&r[0]>=-1&&r[0]<=8&&Number.isInteger(r[1])&&r[1]>=0&&r[1]<n)||new Set(s.records.map(r=>r[1])).size!==n)return s;
  if(!Number.isSafeInteger(s.answers)||s.answers<0||!Number.isSafeInteger(s.errors)||s.errors<0||s.errors>s.answers)return s;
  return {...s,signature:JSON.stringify(current),records:[...s.records.map(r=>[...r]),[-1,n]]};
 }catch(e){return s}
}
'''
v=v.replace('try{saved=JSON.parse(localStorage',upgrade+'try{saved=JSON.parse(localStorage',1)
v=v.replace('if(saved.group&&!valid',"for(const k of ['group','all'])saved[k]=upgradeAppend(saved[k],k);\nif(saved.group&&!valid",1)
v=v.replace('const s=p.progress[k];','const s=upgradeAppend(p.progress[k],k);')
views['practice']=v;write(U/'记忆练习脚本.js',re.search(r'<script>([\s\S]*)</script>',v)[1]);write(P/'迁移测试_新练习.js',re.search(r'<script>([\s\S]*)</script>',v)[1])
views['roots']=views['roots'].replace('</tbody>','<tr><td>s</td><td>正</td><td>归并：止</td><td>政、整、焉、证</td></tr></tbody>')
def rootrow(m):
 cells=re.findall(r'<td>(.*?)</td>',m[0]);name=re.sub('<[^>]+>','',cells[1]) if len(cells)==4 else ''
 if name in examples:return m[0].replace('<td>'+cells[3]+'</td>','<td>'+'、'.join(x['字'] for x in examples[name]['4'])+'</td>')
 return m[0]
views['roots']=re.sub(r'<tr><td>.*?</tr>',rootrow,views['roots'])
views['image']=views['image'].replace('定字底 畏下 疋 龰 止 足 ⻊ 走','定字底 畏下 疋 龰 止 正 足 ⻊ 走').replace('定字底、畏下、疋、龰、止、足、⻊、走','定字底、畏下、疋、龰、止、正、足、⻊、走')
views['text']=put(views['text'],'rows',splitrows)
for k,n in {'query':'拆分查询.html','components':'部件反查.html','practice':'字根练习.html','roots':'字根总表.html','image':'字根图.html','text':'完整拆分表.html'}.items():write(O/n,views[k])
write(O/'完整拆分表.txt',splittext,'utf-8-sig');f=O/'字根键位表.txt';write(f,f.read_text(encoding='utf-8-sig').rstrip()+'\n正\ts\t归并：止\n','utf-8-sig')
shell=put(shell,'views',views)
write(main,shell);write(U/'夜莺啾啾工具箱.html',shell)
for folder in [W/'64_加入鲸凉鹤简词',W/'59_单字当量排行']:
 for f in folder.iterdir():
  if f.is_file() and f.suffix in ['.txt','.json','.html']:
   q=B/f.relative_to(W);q.parent.mkdir(parents=True,exist_ok=True)
   if not q.exists():shutil.copy2(f,q)
with contextlib.redirect_stdout(io.StringIO()):
 runpy.run_path(str(W/'64_加入鲸凉鹤简词/build.py'),run_name='__main__')
 runpy.run_path(str(W/'59_单字当量排行/build.py'),run_name='__main__')
with zipfile.ZipFile(U/'夜莺2.0离线工具包.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in O.rglob('*'):
  if f.is_file():z.write(f,f.relative_to(U))
jout(new/'实装核验.json',{'基线':str(new),'字数':len(D),'单字条目':len(short.splitlines()),'拆分变化':affected,'练习追加':'group149→150，all403→404，旧进度自动迁移及导入兼容','状态':'等待迁移测试'})
print('同步完成，等待测试',new)
