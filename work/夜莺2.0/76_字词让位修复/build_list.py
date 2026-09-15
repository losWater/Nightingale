# -*- coding: utf-8 -*-
"""生成字词让位变更清单（只读码表，只写本目录）。
规则：1 字有简码+四码词→让；2 多词最多让一位；3 字全可让位则整块后移保持原序；
      4 无简码但字频>5000 的字，仅当顶上首选的是二字词时默认让位，三字及以上词不让。
      码位人工指定.json 的码位一律不动。"""
import io,sys,json,html,collections,datetime
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
B='E:/夜莺2.0/work/夜莺2.0'
rank={e['字']:e['字频'] for e in json.load(open(B+'/59_单字当量排行/单字当量排行.json',encoding='utf-8'))}
man=json.load(open(B+'/64_加入鲸凉鹤简词/码位人工指定.json',encoding='utf-8-sig'))
codes=collections.defaultdict(set); order=collections.defaultdict(list)
for line in open(B+'/64_加入鲸凉鹤简词/夜莺2.0含简词字词表_普通格式.txt',encoding='utf-8-sig'):
    p=line.rstrip('\n').rstrip('\r').split('\t')
    if len(p)>=2 and p[1].isalpha(): codes[p[0]].add(p[1]); order[p[1]].append(p[0])
has=lambda w,F: any(len(s)<4 and F.startswith(s) for s in codes[w])
rows=[]
for F,c in order.items():
    if len(F)!=4 or F in man: continue
    ch=[w for w in c if len(w)==1]; wd=[w for w in c if len(w)>1]
    if not ch or not wd: continue
    w1=wd[0]
    why={w:('有简码'+str(sorted(s for s in codes[w] if len(s)<4 and F.startswith(s)))
            if has(w,F) else ('生僻%d>5000'%rank.get(w,99999) if rank.get(w,99999)>5000 and len(w1)==2
                              else '不可让位(%s)'%rank.get(w,99999))) for w in ch}
    ok=all(has(w,F) or (rank.get(w,99999)>5000 and len(w1)==2) for w in ch)
    tgt=(wd[:1]+ch+wd[1:]) if ok else ch+wd
    if tgt==c: continue
    if not ok: t='C_字整组前移'
    elif any(not has(w,F) for w in ch): t='A_生僻字让二字词'
    else: t='B_有简码字让词'
    rows.append({'码':F,'类型':t,'现候选':c,'新候选':tgt,'首选变化':[c[0],tgt[0]],
                 '单字':[{'字':w,'排名':rank.get(w,99999),'判定':why[w]} for w in ch],
                 '词':wd,'顶上首选词字数':len(tgt[0]) if len(tgt[0])>1 else None})
rows.sort(key=lambda r:(r['类型'],min(x['排名'] for x in r['单字'])))
json.dump({'生成时间':datetime.datetime.now().isoformat(timespec='seconds'),
           '规则':['字有简码+四码词→让','多词最多让一位','字全可让位则整块后移保持原序',
                  '无简码但字频>5000：仅二字词可顶，三字及以上不让','人工指定码位不动'],
           '总数':len(rows),'分类':dict(collections.Counter(r['类型'] for r in rows)),
           '变更':rows},open('变更清单.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
e=html.escape
cnt=collections.Counter(r['类型'] for r in rows)
p=['<meta charset="utf-8"><title>字词让位变更清单</title><style>',
 'body{font:15px/1.7 "Microsoft YaHei";background:#f2f1eb;color:#243a3a;margin:24px}',
 'h1{font-size:22px}h2{font-size:17px;margin-top:28px;border-left:4px solid #6b9e93;padding-left:10px}',
 'table{border-collapse:collapse;width:100%;background:#fbfaf6}td,th{border:1px solid #d7ddd1;padding:6px 9px;vertical-align:top}',
 'th{background:#e6ebe2;text-align:left}code{background:#e9eee6;padding:1px 5px;border-radius:3px;font-size:14px}',
 '.o{color:#9a4a3c}.n{color:#2d6b4f;font-weight:600}.m{color:#777;font-size:13px}</style>',
 '<h1>夜莺2.0 字词让位变更清单</h1>',
 '<p class="m">生成：%s ｜ 共 <b>%d</b> 处 ｜ 人工指定码位已排除 ｜ <b>本清单仅供核对，码表尚未改动</b></p>'%(
   datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),len(rows)),
 '<p>规则：①字有简码+四码词→让　②多词最多让一位　③字全可让位则整块后移保持原序　'
 '④无简码但字频&gt;5000 的字，仅当顶上首选的是<b>二字词</b>时让位，三字及以上词不让</p>']
NAME={'A_生僻字让二字词':'A 生僻字(&gt;5000)让位给二字词','B_有简码字让词':'B 有简码的字让位给词',
      'C_字整组前移':'C 有字不可让位 → 单字整组前移'}
for t in ('C_字整组前移','B_有简码字让词','A_生僻字让二字词'):
    sub=[r for r in rows if r['类型']==t]
    p.append('<h2>%s（%d 处）</h2><table><tr><th style="width:64px">码</th><th>现候选</th><th>新候选</th><th style="width:34%%">单字判定</th></tr>'%(NAME[t],len(sub)))
    for r in sub:
        p.append('<tr><td><code>%s</code></td><td class="o">%s</td><td class="n">%s</td><td class="m">%s</td></tr>'%(
            e(r['码']),e('、'.join(r['现候选'])),e('、'.join(r['新候选'])),
            e('；'.join('%s(%d) %s'%(x['字'],x['排名'],x['判定']) for x in r['单字']))))
    p.append('</table>')
open('变更清单.html','w',encoding='utf-8').write(''.join(p))
print('共 %d 处：%s' % (len(rows),dict(cnt)))
print('已生成 变更清单.json 与 变更清单.html（未改动任何码表）')
