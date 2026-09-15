from pathlib import Path
import collections,re,json,html
P=Path(__file__).resolve().parent

def reorder(combined,source,restore,merges):
 short={t for c,ts in combined.items() if len(c)<4 for t in ts if len(t)==1}
 ranks=collections.defaultdict(list)
 for line,l in enumerate(source.read_text(encoding='utf-8-sig').splitlines(),1):
  m=re.fullmatch(r'([a-z]+)=(\d+),(.+)',l)
  if not m:continue
  old,rank,t=m.groups();c=old
  if len(t)<2 or len(c)<4:continue
  if len(c)==len(t)*2:c=''.join(restore(ch,c[i*2:i*2+2]) for i,ch in enumerate(t))
  elif len(c)==4 and len(t)==3:c=c[:2]+restore(t[-1],c[2:])
  c=merges.get((t,c),c)
  if len(c)==4 and len(t)>=4 and re.fullmatch(r'[\u3400-\u9fff]+',t):
   c=''.join('y' if t[i]=='一' and k=='e' else k for k,i in zip(c,[0,1,2,len(t)-1]))
  ranks[c,t].append((old,int(rank),line))
 changes=[];merged=[];unranked=[];leading=0
 for c,ts in list(combined.items()):
  if len(c)<4:continue
  chars=[t for t in ts if len(t)==1];words=[t for t in ts if len(t)>1]
  groups=collections.defaultdict(list);missing=[]
  for t in words:
   meta=ranks.get((c,t))
   if meta:
    old,rank,line=min(meta,key=lambda r:r[2]);groups[old].append((rank,line,t))
   else:missing.append(t)
  order=sorted(groups,key=lambda k:min(r[1] for r in groups[k]))
  ordered=[t for k in order for rank,line,t in sorted(groups[k])]+missing
  if len(groups)>1:merged.append({'码':c,'原码组':order,'词序':ordered,'说明':'各组内按原候选序，组间暂按源文件首次出现次序，未视为跨组词频'})
  if missing:unranked.append({'码':c,'词':missing,'说明':'未匹配到原全码候选序，暂排其他全码词后'})
  # A word may precede the contiguous character block only if every character has a short code.
  lead=bool(chars and ordered and all(t in short for t in chars))
  after=(ordered[:1]+chars+ordered[1:]) if lead else chars+ordered
  leading+=int(lead)
  assert set(after)==set(ts) and len(after)==len(ts)
  assert [t for t in after if len(t)==1]==chars
  if chars:
   first=after.index(chars[0]);assert first<=1
   assert after[first:first+len(chars)]==chars
   if any(t not in short for t in chars):assert first==0
  if after!=ts:changes.append({'码':c,'调整前':ts,'调整后':after})
  combined[c]=after
 stats={'调整全码码位':len(changes),'词占首选后紧接单字的码位':leading,'待跨组比较码位':len(merged),'缺原全码词序码位':len(unranked),'规则':'无简码字所在码位单字整组在前；同码字均有简码时，只允许一个全码词首选，随后全部单字，再排剩余词。四字及以上词参与同一原码组候选序排序；跨组次序暂定；二三简不变。'}
 data={'摘要':stats,'变化':changes,'合流待比较':merged,'缺词序':unranked}
 (P/'全码最多让一位.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 esc=html.escape
 page='<meta charset="utf-8"><title>全码最多让一位</title><style>body{font:16px/1.7 Microsoft YaHei;background:#f2f1eb;color:#243a3a;margin:24px}table{border-collapse:collapse}td,th{border:1px solid #d7ddd1;padding:10px;text-align:left}</style><h1>全码最多让一位</h1><pre>'+esc(json.dumps(stats,ensure_ascii=False,indent=2))+'</pre><table><tr><th>码</th><th>调整前</th><th>调整后</th></tr>'
 for r in changes:page+='<tr><td>'+esc(r['码'])+'</td><td>'+esc('、'.join(r['调整前']))+'</td><td>'+esc('、'.join(r['调整后']))+'</td></tr>'
 (P/'全码最多让一位.html').write_text(page+'</table>',encoding='utf-8')
 return combined,stats
