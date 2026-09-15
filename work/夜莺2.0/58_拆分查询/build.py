from pathlib import Path
import json,collections
P=Path(__file__).resolve().parent;W=P.parent;T=W/'54_补删鹿旁保留羊南心四起点试跑'
def read(f):return json.loads(f.read_text(encoding='utf-8-sig'))
b=Path(read(T/'二简人工复核/当前裁定基线.json')['目录']);mapping=read(T/'jobs/t1_projection/final_config.json')['form']['mapping'];mapping.update(read(b/'根位覆盖.json'))
roots={}
for g in read(T/'frozen/当前完整根表.json')['根组']:
 for rid,label in zip(g['根形ID'],g['根形']):roots[rid]={'根':label,'键':mapping['G%03d'%g['序号']],'组':g['根组']}
codes=collections.defaultdict(list);candidates=collections.defaultdict(list)
for l in (b/'普通纯单字表.txt').read_text(encoding='utf-8-sig').splitlines():
 c,k=l.split('\t');candidates[k].append(c);codes[c].append(k)
freq={r['字']:r['新排名'] for r in read(W/'32_多来源字频重建/试验整字频率.json')['字表']}
rows={}
for r in read(W/'55_拆分继承核验/全部拆分对照.json'):
 c=r['字'];rows[c]={'根':[roots[t] for t in r['新根ID']],'旧拆':r['旧拆'],'新拆':r['新拆'],'状态':r['状态'],'人工':r['人工校对'],'排名':freq.get(c),'编码':[{'码':k,'位':candidates[k].index(c)+1,'同码':candidates[k]} for k in codes[c]]}
assert rows['丢']['新拆']=='撇 ＋ 土 ＋ 厶'
assert ''.join([rows['丢']['根'][0]['键'],rows['丢']['根'][-1]['键']])=='fh'
assert any(x['码']=='lqq' for x in rows['六']['编码'])
assert roots[next(t for t,v in roots.items() if v['根']=='赢字架')]['键']=='e'
public_rows={c:{k:v for k,v in row.items() if k not in ('旧拆','状态','人工')} for c,row in rows.items()}
data=json.dumps(public_rows,ensure_ascii=False).replace('<','\u003c')
template=(P/'template.html').read_text(encoding='utf-8');(P/'夜莺2.0拆分查询.html').write_text(template.replace('__DATA__',data).replace('__ROOTS__',json.dumps(list({(v['根'],v['键']):v for v in roots.values()}.values()),ensure_ascii=False).replace('<','\\u003c')),encoding='utf-8')
print('已生成',len(rows),'字；当前基线',b)
