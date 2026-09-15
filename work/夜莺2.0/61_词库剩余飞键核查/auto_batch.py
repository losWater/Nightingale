from pathlib import Path
import json,runpy,collections,re,html
P=Path(__file__).resolve().parent;W=P.parent;V=W/'56_鲸凉鹤原词库字词版'
read=lambda f:json.loads(f.read_text(encoding='utf-8-sig'))
policy=runpy.run_path(str(V/'restore_fly.py'));dc=policy['m']['double_code']
raw=read(P/'待核二字词.json');lex=collections.defaultdict(set)
for line in policy['m']['LEX'].read_text(encoding='utf-8-sig').splitlines():
 q=line.split('\t')
 if len(q)<2 or len(q[0])!=2:continue
 py=q[1].split()
 if len(py)!=2:continue
 try:cs=[dc(policy['m']['syllable'](x)) for x in py]
 except (KeyError,IndexError):continue
 if all(cs):lex[q[0]].add(''.join(cs))
# Only merge an exceptional code when the same word already has exactly one normal-code candidate.
current=collections.defaultdict(set)
for l in (V/'鲸凉鹤非简词_普通码表.txt').read_text(encoding='utf-8-sig').splitlines():
 w,k=l.split('\t');current[w].add(k)
changes=[];accepted=[];left=[]
for r in raw:
 w,k=r['词'],r['待核码'];e=lex[w]
 if k in e:
  accepted.append({**r,'处理':'整词资料支持现码；原码保留','证据':'Chai整词拼音'});continue
 # Restrict replacement to special oj/oo placeholders with matching existing normal entry.
 special=any(b['码'] in ['oj','oo'] for b in r['异常音节'])
 choices=set(r['正常音码候选'])
 if special and len(choices)==1:
  target=next(iter(choices))
  if target in current[w] and (not e or target in e):changes.append({**r,'新码':target,'处理':'特殊入口合并到源词库已有正常码'});continue
 left.append({**r,'处理':'不处理，保持本轮前编码；不列人工待办'})
for name,data in [('自动合并清单',changes),('原码通过清单',accepted),('保留不处理清单',left)]: (P/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
(V/'整词特殊码自动合并.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
summary={'本轮告警':len(raw),'确认原码无需修改':len(accepted),'合并特殊入口':len(changes),'保留不处理':len(left),'说明':'不新增词，不猜测读音；保留全部词文本。只处理本轮明确依据，余项封存不列人工任务。'}
(P/'自动处理摘要.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
page='<meta charset="utf-8"><title>词库自动处理结果</title><style>body{font:17px/1.7 Microsoft YaHei;margin:30px}td,th{border:1px solid #ddd;padding:9px}table{border-collapse:collapse}</style><h1>词库自动处理结果</h1><p>'+html.escape(str(summary))+'</p><p>剩余项保留，不需要逐条人工审核。</p><table><tr><th>词</th><th>原入口</th><th>正常入口</th></tr>'
for r in changes:page+='<tr>'+''.join('<td>'+html.escape(r[k])+'</td>' for k in ['词','待核码','新码'])+'</tr>'
(P/'自动处理结果.html').write_text(page+'</table>',encoding='utf-8');print(summary);print(changes[:3])
