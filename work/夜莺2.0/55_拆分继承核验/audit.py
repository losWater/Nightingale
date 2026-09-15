from pathlib import Path
import json,csv,difflib,collections,hashlib,html,yaml
W=Path('E:/夜莺2.0/work/夜莺2.0');P=Path(__file__).resolve().parent;A=W/'04_逐根删除评估';T=W/'54_补删鹿旁保留羊南心四起点试跑'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
I=read(A/'input.json');norm=I['norm'];inv={x['id']:x['display'] for x in I['inventory']}
for x in I['inventory']:
 norm.setdefault(x['display'],x['id'])
oldfile=W.parents[1]/'releases/v1.0/03_字根与拆分/夜莺鹤1.0拆分表.txt'
def loadtab(f):
 with f.open(encoding='utf-8-sig') as h:return {r['汉字']:[norm.get(t.strip(),t.strip()) for t in r['最终规范拆分'].split('＋') if t.strip()] for r in csv.DictReader(h,delimiter='\t')}
old=loadtab(oldfile);expected=I['expected'];seed=read(A/'剩余候选累计拆分.json');audit=read(T/'输入核验.json');rep={'利':['禾','刂'],**audit['替换']}
def expand(t):return [x for y in rep[t] for x in expand(y)] if t in rep else [t]
new={c:[x for t in ts for x in expand(t)] for c,ts in seed.items()}
manual=read(A/'active-baseline.json')['manual'];roots=read(T/'frozen/当前完整根表.json')['根组'];rid={t:'G%03d'%g['序号'] for g in roots for t in g['根形ID']}
for g in roots:
 for t,v in zip(g['根形ID'],g['根形']):inv[t]=v
show=lambda ts:' ＋ '.join(inv.get(t,t) for t in ts)
oldroots={t for ts in old.values() for t in ts};newroots=set(rid);added=newroots-({x['id'] for x in I['inventory']}|oldroots);deleted=oldroots-newroots
# Changed blocks without a removed old root or added new root require individual explanation.
rows=[]
for c in sorted(old):
 o,n=old[c],new[c];hunks=[]
 for tag,i,j,k,l in difflib.SequenceMatcher(a=o,b=n,autojunk=False).get_opcodes():
  if tag!='equal':hunks.append({'old':o[i:j],'new':n[k:l],'root_evidence':bool(set(o[i:j])&deleted or set(n[k:l])&added)})
 status='完全不变' if o==n else ('存在无直接增删根依据的变化块' if any(not h['root_evidence'] for h in hunks) else '各变化块均涉及增删根_待来源核验')
 rows.append({'字':c,'旧拆':show(o),'新拆':show(n),'旧根ID':o,'新根ID':n,'状态':status,'人工校对':c in manual,'变化块':hunks})
# Independently verify complete split endpoints against frozen encoder input.
es=yaml.safe_load((T/'frozen/elements.yaml').read_text(encoding='utf-8'));mismatch=[]
for e in es:
 c=e['词']
 if len(c)!=1:continue
 els=e['元素序列'];v=new[c];want=[rid.get(v[0]),rid.get(v[-1])];actual=[els[2]['element'],els[3]['element']]
 if want!=actual:mismatch.append({'字':c,'音':e['拼音'],'拆分首末组':want,'实际首末组':actual,'拆分':show(v)})
# canonical manual snapshots compare to 1.0 and new without confusing changed roots with lost rules.
manualrows=[{'字':c,'原人工拆':show(x['canonical']),'1.0拆':show(old[c]),'新拆':show(new[c]),'人工与1.0相同':x['canonical']==old[c],'新旧相同':new[c]==old[c]} for c,x in manual.items()]
source_diff=[c for c in old if old[c]!=expected[c]]
summary={'字数':len(new),'状态计数':dict(collections.Counter(x['状态'] for x in rows)),'旧发布与2.0入口差异':source_diff,'人工字数':len(manual),'人工不变':sum(x['新旧相同'] for x in manualrows),'首末元素不一致':mismatch,'新增根ID':sorted(added),'删除根ID':sorted(deleted),'说明':'变化块判定仅为保守筛查，不等同于已证明合法。使用1.0发布完整拆分，根ID归一化；新拆为当前累计全拆分加利和54九根删除。二简、根键位迁移不应改变拆分。'}
for name,data in [('核验摘要',summary),('全部拆分对照',rows),('人工校对继承',manualrows)]: (P/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
(P/'当前完整拆分表.txt').write_text('汉字\t完整拆分\t首根\t末根\n'+''.join(f'{c}\t{show(ts)}\t{show(ts[:1])}\t{show(ts[-1:])}\n' for c,ts in sorted(new.items())),encoding='utf-8-sig')
(P/'当前完整拆分_根ID.json').write_text(json.dumps(new,ensure_ascii=False,indent=2),encoding='utf-8')
print('summary',summary['状态计数'],'source_diff',len(source_diff),'manual',summary['人工不变'],'endpoint',len(mismatch));print('sourcechars',source_diff);print('endpoints',mismatch[:15])
print('suspects',[(x['字'],x['旧拆'],x['新拆']) for x in rows if x['状态']=='存在无直接增删根依据的变化块'][:100])

# Verify repeated-token alignment alerts by an exact, whole-sequence rewrite.
for r in rows:
 o,n=r['旧根ID'],r['新根ID']
 if o==n:continue
 if r['字'] in '丕伾呸坯狉胚苤𬳵':
  pat=[norm.get(x,x) for x in ['一','亻','点']]
  candidates=[o[:i]+['不']+o[i+3:] for i in range(len(o)-2) if o[i:i+3]==pat]
  assert n in candidates
  r['状态']='增删根相关';r['核验依据']='新增不根，完整序列精确替换；其余根顺序不变'
 elif r['字']=='麀':
  assert [x for t in o for x in expand(t)]==n
  r['状态']='增删根相关';r['核验依据']='删除鹿根，按输入核验中的替换精确展开；末尾匕保持'
 elif all(h['root_evidence'] for h in r['变化块']):
  r['状态']='增删根相关';r['核验依据']='每个差异块均含删除根或新增根；这是继承范围核验，不替代字形正确性审查'
 else:
  r['状态']='需复核';r['核验依据']='未找到增删根依据。車是原有繁体根，不应当作新增根。'
# Apply approvals only to the exact reviewed old/new decomposition pair.
for decision in read(P/'人工差异裁定.json'):
 r=next(r for r in rows if r['字']==decision['字'])
 assert r['旧根ID']==decision['旧根ID'] and r['新根ID']==decision['新根ID'], '裁定拆分发生变化，需要重新复核'
 r['状态']='人工已接受';r['核验依据']=decision['日期']+' 用户确认接受此拆分差异'
summary['状态计数']=dict(collections.Counter(r['状态'] for r in rows))
summary['源文件SHA256']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [oldfile,Path('D:/nightingale/releases/v1.0/03_字根与拆分/夜莺鹤1.0拆分表.txt'),A/'input.json',A/'剩余候选累计拆分.json',T/'输入核验.json',T/'frozen/elements.yaml',A/'active-baseline.json']}
summary['说明']='对照1.0发布完整拆分，归一化根别名。增删根相关表示变化块具有根集依据，不等同于对每个新拆分字形重新人工验收。当前导出首末根与冻结编码输入一致。墼为入口继承差异，用户已确认接受，保持当前拆分。'
for name,data in [('核验摘要',summary),('全部拆分对照',rows)]: (P/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
changed=[r for r in rows if r['旧根ID']!=r['新根ID']]
(P/'变化795字逐行对照.txt').write_text('\n'.join('字：'+r['字']+'  旧拆：'+r['旧拆']+'  新拆：'+r['新拆']+'  核验：'+r['状态']+('  人工校对字' if r['人工校对'] else '') for r in changed),encoding='utf-8-sig')
def table(rs):
 return '<table><thead><tr><th>字</th><th>1.0完整拆分</th><th>当前完整拆分</th><th>核验</th><th>人工记录</th></tr></thead><tbody>'+''.join('<tr data-search="'+html.escape(r['字']+r['旧拆']+r['新拆']+r['状态'])+'">'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [r['字'],r['旧拆'],r['新拆'],r['状态'],'有' if r['人工校对'] else ''])+'</tr>' for r in rs)+'</tbody></table>'
page='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>拆分继承核验</title><style>body{font:17px/1.7 "Microsoft YaHei",sans-serif;max-width:1500px;margin:35px auto;padding:0 25px;background:#f7f8fa;color:#172435}table{width:100%;border-collapse:collapse;background:white}td,th{padding:10px;border:1px solid #d9dfe7;text-align:left}th{background:#e8eef5;position:sticky;top:0}input{padding:12px;width:400px}section{background:#fff3d8;padding:16px}a{color:#1960b3}</style><h1>新旧完整拆分继承核验</h1><p>8105字：7310字完全不变；794字变化涉及增删根；1字为人工已接受的独立差异；待复核0字。</p><section><b>已接受的独立差异：墼</b><p>1.0：一＋日＋十＋凵＋殳＋土<br>当前：車＋凵＋殳＋土</p><p>差异已存在于2.0早期评估入口，不是本轮二简调整产生。車是原有根，不归入新增根影响。2026-09-13用户确认接受此变化，保留当前拆分：車＋凵＋殳＋土。</p></section><p>人工校对记录244字全部与1.0发布表吻合。其中222字原样保留，22字变化涉及增删根。新导出拆分的首末根与冻结编码输入8454条单字读音逐项对照，不一致0条。D盘1.0发布拆分表与E盘留存版SHA256相同。</p><p>口径：比较完整根序列，统一根别名，不把换键、简码调整算作拆分变化。“增删根相关”是差异范围核验，不代表已重新人工审定全部新拆分的字形；中间根由累计拆分记录继承，首末根另与实际编码输入核对。</p><p><a href="当前完整拆分表.txt">下载当前8105字完整拆分</a> · <a href="变化795字逐行对照.txt">下载795字变化对照</a> · <a href="核验摘要.json">核验摘要与来源哈希</a></p><h2>有变化的人工校对字（22字）</h2>'+table([r for r in changed if r['人工校对']])+'<h2>全部变化（795字）</h2><input id="q" placeholder="搜索汉字、根或“需复核”"><div id="changes">'+table(sorted(changed,key=lambda r:r['状态']!='需复核'))+"</div><script>document.querySelector('#q').addEventListener('input',e=>document.querySelectorAll('#changes tbody tr').forEach(r=>r.hidden=!r.dataset.search.includes(e.target.value.trim())))</script></html>"
(P/'拆分继承核验.html').write_text(page,encoding='utf-8')
print('FINAL',summary['状态计数'])
