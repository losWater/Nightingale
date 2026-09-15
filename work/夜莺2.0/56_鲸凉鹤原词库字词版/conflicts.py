from pathlib import Path
import json,collections,re,html
P=Path(__file__).resolve().parent;W=P.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
meta=read(P/'生成摘要.json');base=Path(meta['单字来源']);chars=collections.defaultdict(list);short=set()
for l in base.read_text(encoding='utf-8-sig').splitlines():
 c,k=l.split('\t');chars[k].append(c)
 if len(k)<4:short.add(c)
words=collections.defaultdict(list)
for l in (P/'鲸凉鹤非简词_普通码表.txt').read_text(encoding='utf-8-sig').splitlines():
 w,k=l.split('\t');words[k].append(w)
cr={r['字']:r['新排名'] for r in read(W/'32_多来源字频重建/试验整字频率.json')['字表']}
wr={r['词']:r['二字词排名'] for r in map(json.loads,(W/'08_词库与词频重建/二字词60000_鲸凉鹤补全后.jsonl').read_text(encoding='utf-8-sig').splitlines())}
cb=[500,1500,3000,6000];wb=[2000,5000,10000,20000,50000]
def band(r,b):return next((i for i,n in enumerate(b) if r<=n),len(b))
rows=[];mats=[[[0]*6 for _ in range(5)] for _ in range(2)]
for k,ws in words.items():
 for c in chars[k]:
  for w in ws:
   r={'码':k,'字':c,'字频名次':cr.get(c,999999),'词':w,'词频名次':wr.get(w),'有简码':c in short};rows.append(r)
   i,j=band(cr.get(c,999999),cb),band(wr.get(w,999999),wb);mats[0][i][j]+=1
   if c not in short:mats[1][i][j]+=1
active=[r for r in rows if not r['有简码']]
oldwords=collections.defaultdict(list)
for l in (base.parent/'无简词字词表.txt').read_text(encoding='utf-8-sig').splitlines():
 m=re.fullmatch(r'([a-z]+)=\d+,(.+)',l)
 if m and len(m[2])>1:oldwords[m[1]].append(m[2])
def stat(ws):
 pairs=[(k,c,w) for k,v in ws.items() for c in chars[k] for w in v]
 return {'词条':sum(map(len,ws.values())),'同码位置':len({k for k,c,w in pairs}),'纸面冲突对':len(pairs),'排除有简字后冲突对':sum(c not in short for k,c,w in pairs),'排除有简字后同码位置':len({k for k,c,w in pairs if c not in short})}
summary={'本次':stat(words),'原配套词库_使用相同当前单字重算':stat(oldwords),'涉及单字':len({r['字'] for r in rows}),'无简码冲突单字':len({r['字'] for r in active}),'被无简码单字压后的词条':len({(r['码'],r['词']) for r in active}),'前1500字_前10000词_纸面':sum(r['字频名次']<=1500 and (r['词频名次'] or 999999)<=10000 for r in rows),'前1500字_前10000词_无简字':sum(r['字频名次']<=1500 and (r['词频名次'] or 999999)<=10000 for r in active),'分档矩阵':mats,'限制':'当前试用词库，未知飞键未清零。按整字是否有任意简码区分，与当前生成规则一致；不代表每个读音都有可用简码。不计词词重码。不等同实战选重率。词频仅使用已有六万二字词排名，其余列为排名50000后或未覆盖。'}
for name,data in [('字词冲突统计',summary),('字词冲突逐对明细',rows)]: (P/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
cl=['1–500','501–1500','1501–3000','3001–6000','6001以后'];wl=['1–2000','2001–5000','5001–10000','10001–20000','20001–50000','50000后/未覆盖']
def table(headers,data):return '<table><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in data)+'</table>'
p='<meta charset="utf-8"><title>鲸凉鹤词版字词冲突</title><style>body{font:17px/1.7 Microsoft YaHei;max-width:1450px;margin:35px auto;padding:20px;color:#172b40}table{border-collapse:collapse;width:100%;margin:20px 0}td,th{border:1px solid #ddd;padding:9px;text-align:left}th{background:#eef3f7}</style><h1>鲸凉鹤词版字词冲突</h1><p>'+summary['限制']+'</p><h2>同一单字表，更换词库前后</h2>'
p+=table(['词库']+list(summary['本次']),[[label]+list(summary[key].values()) for label,key in [('原配套词库','原配套词库_使用相同当前单字重算'),('鲸凉鹤词库','本次')]])
for title,mat in zip(['全码纸面碰撞（包含有简码字）','排除有简码单字后的碰撞'],mats):p+='<h2>'+title+'</h2>'+table(['字频档 / 词频档']+wl,[[cl[i]]+r for i,r in enumerate(mat)])
p+='<p>有简让全改变的是候选顺序，不会删除同码关系。无简码单字仍在词前；有简码单字的全码在词后。</p><h2>高频区域残留（前1500字 × 前10000词，无简码字）</h2>'
red=sorted([r for r in active if r['字频名次']<=1500 and (r['词频名次'] or 999999)<=10000],key=lambda r:(r['字频名次'],r['词频名次']))
p+=table(['编码','字','字频名次','词','词频名次'],[[r[k] for k in ['码','字','字频名次','词','词频名次']] for r in red])
p+='<p><a href="字词冲突逐对明细.json">全部冲突明细</a> · <a href="字词冲突统计.json">统计数据</a></p>'
(P/'字词冲突对照.html').write_text(p,encoding='utf-8');print(json.dumps({k:v for k,v in summary.items() if k!='分档矩阵'},ensure_ascii=False,indent=2));print('红区',red)
