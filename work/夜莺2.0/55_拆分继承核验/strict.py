from pathlib import Path
import json,runpy,contextlib,io,html,difflib,collections
with contextlib.redirect_stdout(io.StringIO()):s=runpy.run_path(str(Path(__file__).with_name('audit.py')))
globals().update({k:s[k] for k in ['P','A','I','norm','old','new','added','deleted','read','show']})
# Only explicit recorded deletion rules; restored roots are excluded.
rules={**I['confirmed'],**s['rep']}
for x in list(read(A/'review-deletions.json').values())+read(A/'wenjiao-selected.json'):
 if x['id'] in deleted:rules[x['id']]=x['replacement']
for k,v in {'署':['罒','耂','日'],'居':['尸','古'],'贤字头':['丨','丨','又'],'览字头':['丨','丨','卧人','丶']}.items():rules[norm.get(k,k)]=[norm.get(t,t) for t in v]
rules={norm.get(k,k):[norm.get(t,t) for t in v] for k,v in rules.items() if norm.get(k,k) in deleted}
# Reverse newly introduced standalone roots using their pre-change full decomposition.
add_rules={k:old[k] for k in added if k in old and old[k]!=[k]}
# Explicit accepted non-standalone root boundaries from current_state.py and session rulings.
rules.update({'角':['⺈','用'],'击':['二','山']})
add_rules.update({'\ue08c':['冂',norm['举字底']],'\ue05f':['龶','5','丿'],'\ue021':[norm['卧人'],'一','止'],'攴':[norm.get('⺊','⺊'),'又']})
(P/'局部替换规则.json').write_text(json.dumps({'删根展开':rules,'新根还原':add_rules},ensure_ascii=False,indent=2),encoding='utf-8')
def expand(t,stack=()):
 if t in stack:return [t]
 v=rules.get(t,add_rules.get(t))
 return [x for a in v for x in expand(a,stack+(t,))] if v else [t]
def seq(ts):return [x for t in ts for x in expand(t)]
rows=[]
for c in old:
 if old[c]==new[c]:continue
 a,b=seq(old[c]),seq(new[c]);res=[]
 for tag,i,j,k,l in difflib.SequenceMatcher(a=a,b=b,autojunk=False).get_opcodes():
  if tag!='equal':res.append(show(a[i:j])+' → '+show(b[k:l]))
 status='局部精确替换通过' if a==b else '仍有差异，需逐项核对'
 if c=='墼':status='独立人工裁定已接受'
 rows.append({'字':c,'旧拆':show(old[c]),'新拆':show(new[c]),'状态':status,'展开旧':show(a),'展开新':show(b),'残留差异':'；'.join(res)})
(P/'局部边界严格核验.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(collections.Counter(r['状态'] for r in rows))
for r in rows:
 if r['状态']=='仍有差异，需逐项核对':print(r['字'],r['旧拆'],'=>',r['新拆'],'残留',r['残留差异'])

counts=collections.Counter(r['状态'] for r in rows)
page="""<meta charset="utf-8"><title>拆分局部边界核验</title><style>body{font:17px/1.7 Microsoft YaHei;margin:35px;color:#182b3a}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:10px;text-align:left}th{position:sticky;top:0;background:#edf2f6}input{padding:12px;width:400px}</style><h1>拆分变化部分严格核验</h1><p>7310字完全不变；794字局部替换通过；墼1字为已接受独立差异。</p><p>按记录的删根展开规则展开旧根；把新增根还原为旧拆分片段，再比较完整根序列。要求所有剩余部分内容和顺序一致，不再使用“变化块含增删根即可”的判定。</p><p>此核验检查根序列继承和局部替换范围，不等于重新人工审定字形。没有修改实际码表。</p><p><a href="局部替换规则.json">规则明细</a> · <a href="局部边界严格核验.json">完整核验数据</a></p><input placeholder="搜索汉字" oninput="document.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.textContent.includes(this.value))"><table><thead><tr><th>字</th><th>原拆分</th><th>新拆分</th><th>结果</th></tr></thead><tbody>"""
for r in rows:page+='<tr>'+''.join('<td>'+html.escape(r[k])+'</td>' for k in ['字','旧拆','新拆','状态'])+'</tr>'
page+='</tbody></table>'
(P/'拆分局部边界核验.html').write_text(page,encoding='utf-8')
assert counts['局部精确替换通过']==794 and counts['独立人工裁定已接受']==1 and counts['仍有差异，需逐项核对']==0
