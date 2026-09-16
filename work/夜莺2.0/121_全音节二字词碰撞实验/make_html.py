# -*- coding: utf-8 -*-
"""把 121 实验做成可筛选的 HTML：按字频档的汇总 + 每个"全码像二字词"的字（码、有无简码、对应的音节对）。"""
import io, sys, os, json, re, collections, html as _h
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__))
J = lambda p: json.load(open(p, encoding='utf-8-sig'))
syl = collections.defaultdict(set)
for r in J(W + '/54_补删鹿旁保留羊南心四起点试跑/frozen/字音基准.json'): syl[r['音码']].add(re.sub(r'[1-5]$', '', r['拼音']))
rank = {r['字']: r['新排名'] for r in J(W + '/32_多来源字频重建/试验整字频率.json')['字表']}
full = collections.defaultdict(list); short = collections.defaultdict(list)
for l in open(W + '/78_纯单字表核验/夜莺2.0纯单字表_普通格式.txt', encoding='utf-8-sig'):
    q = l.rstrip('\r\n').split('\t')
    if len(q) < 2 or len(q[0]) != 1: continue
    (full[q[0]].append(q[1]) if len(q[1]) == 4 else short[q[0]].append(q[1]))
def band(r):
    for name, a, b in [('1–500', 1, 500), ('501–1500', 501, 1500), ('1501–3000', 1501, 3000), ('3001–6000', 3001, 6000), ('6001–8105', 6001, 99999)]:
        if a <= r <= b: return name
    return '无频'
rows = []
for c, ks in full.items():
    like = [k for k in ks if k[:2] in syl and k[2:] in syl]
    if not like: continue
    rows.append({'字': c, '频': rank.get(c, 0), '档': band(rank.get(c, 99999)), '码': like, '简码': short.get(c, []),
                 '音节': ['%s+%s' % ('/'.join(sorted(syl[k[:2]])[:2]), '/'.join(sorted(syl[k[2:]])[:2])) for k in like]})
rows.sort(key=lambda r: r['频'] or 99999)
summary = J(H + '/按字频档.json')
data = json.dumps(rows, ensure_ascii=False).replace('<', '\\u003c')
sumhtml = '<table><thead><tr><th>字频档</th><th>字数</th><th>全码像二字词</th><th>占比</th><th>有简码（让位）</th><th>无简码（字占首选）</th></tr></thead><tbody>' + ''.join(
    '<tr><td>%s</td><td>%d</td><td>%d</td><td>%.1f%%</td><td>%d</td><td>%d</td></tr>' % (s['档'], s['字数'], s['像二字词'], s['像二字词'] / s['字数'] * 100, s['有简码'], s['无简码']) for s in summary) + '</tbody></table>'
page = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>全音节二字词碰撞 · 夜莺2.0</title>
<style>*{box-sizing:border-box}body{margin:0;background:#f2f1eb;color:#243a3a;font:17px/1.6 "Microsoft YaHei",sans-serif}main{max-width:1150px;margin:auto;padding:20px}h1{margin:0 0 6px;font-size:24px}h2{font-size:19px;margin:22px 0 8px}p.note{margin:0 0 14px;color:#61716b;font-size:14px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:12px}input{font:inherit;padding:8px 10px;border:1px solid #d7ddd1;border-radius:6px;min-width:200px}button{font:inherit;padding:7px 12px;border:1px solid #d7ddd1;border-radius:6px;background:#faf9f4;cursor:pointer}button[aria-pressed=true]{background:#243a3a;color:#f2f1eb;border-color:#243a3a}
table{width:100%;border-collapse:collapse;background:#faf9f4;margin-bottom:8px}th,td{padding:8px 10px;border:1px solid #d7ddd1;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#edf0e6;position:sticky;top:0}td.z{font-size:24px;text-align:center;width:56px}td.n{text-align:right;width:64px;color:#61716b}code{background:#edf0e6;padding:1px 5px;border-radius:4px}
.no{color:#8a2d2d;font-weight:600}@media(max-width:600px){main{padding:10px}th,td{padding:6px}td.z{font-size:20px}}</style></head>
<body><main><h1>全音节二字词碰撞</h1><p class="note">小鹤双拼实际用到 405 个音节，两两组合 164025 个假想二字词（码 = 两个音码拼起来）。下面列出全码"长得像二字词"的字：后两键恰好是一个合法音节。无简码的字在词来了时仍占首选。范围 8105 字，理想情况推演，不代表真实词库。</p>
<h2>按字频档</h2>__SUM__
<h2>逐字清单</h2><div class="bar"><input id="q" placeholder="输入字、码或音节筛选"><span id="tabs"></span><span id="count"></span></div>
<table><thead><tr><th>字</th><th>字频</th><th>档</th><th>像二字词的全码</th><th>对应音节</th><th>简码</th></tr></thead><tbody id="out"></tbody></table></main>
<script>const rows=__DATA__;let f='全部';const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const q=document.querySelector('#q'),out=document.querySelector('#out'),tabs=document.querySelector('#tabs');
const filters={'全部':r=>true,'无简码':r=>!r.简码.length,'有简码':r=>r.简码.length>0,'1–500':r=>r.档==='1–500','501–1500':r=>r.档==='501–1500','1501–3000':r=>r.档==='1501–3000','3001–6000':r=>r.档==='3001–6000','6001–8105':r=>r.档==='6001–8105'};
function render(){const t=q.value.trim().toLowerCase();const a=rows.filter(r=>filters[f](r)&&(!t||r.字===t||r.码.some(k=>k.includes(t))||r.音节.some(s=>s.includes(t))));
out.innerHTML=a.map(r=>`<tr><td class="z">${esc(r.字)}</td><td class="n">${r.频||'—'}</td><td>${esc(r.档)}</td><td>${r.码.map(k=>'<code>'+esc(k)+'</code>').join(' ')}</td><td>${r.音节.map(esc).join('；')}</td><td>${r.简码.length?r.简码.map(k=>'<code>'+esc(k)+'</code>').join(' '):'<span class="no">无</span>'}</td></tr>`).join('');document.querySelector('#count').textContent='共 '+a.length+' 字';}
tabs.innerHTML=Object.keys(filters).map(c=>`<button type="button" data-c="${esc(c)}" aria-pressed="${c===f}">${esc(c)} ${rows.filter(filters[c]).length}</button>`).join('');
tabs.querySelectorAll('button').forEach(b=>b.onclick=()=>{f=b.dataset.c;tabs.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));render();});q.oninput=render;render();</script></body></html>'''
open(H + '/碰撞清单.html', 'w', encoding='utf-8').write(page.replace('__SUM__', sumhtml).replace('__DATA__', data))
print('已生成', len(rows), '字')
