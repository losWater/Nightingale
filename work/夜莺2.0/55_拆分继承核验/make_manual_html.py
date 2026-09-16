# -*- coding: utf-8 -*-
"""把"人工校对"的拆分导出为可筛选的 HTML（本地打开）。分类：1.0 人工定 / 第十九批 正 / 根集变动机械结果。"""
import io, sys, os, json, html
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
W = 'E:/夜莺2.0/work/夜莺2.0'; H = os.path.dirname(os.path.abspath(__file__))
J = lambda p: json.load(open(p, encoding='utf-8-sig'))
d = J(H + '/全部拆分对照.json'); rank = {r['字']: r['新排名'] for r in J(W + '/32_多来源字频重建/试验整字频率.json')['字表']}
man = sorted([r for r in d if r.get('人工校对')], key=lambda r: rank.get(r['字'], 99999))
def cat(r):
    why = r.get('核验依据') or ''
    if '第十九批' in why: return '第十九批·正'
    if r['状态'] == '增删根相关': return '根集变动'
    return '1.0 人工定'
rows = [{'字': r['字'], '频': rank.get(r['字'], 0), '现': r['新拆'], '旧': r['旧拆'], '类': cat(r), '据': r.get('核验依据') or ''} for r in man]
counts = {}
for x in rows: counts[x['类']] = counts.get(x['类'], 0) + 1
data = json.dumps(rows, ensure_ascii=False).replace('<', '\\u003c')
page = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>人工规定的拆分 · 夜莺2.0</title>
<style>*{box-sizing:border-box}body{margin:0;background:#f2f1eb;color:#243a3a;font:17px/1.6 "Microsoft YaHei",sans-serif}main{max-width:1150px;margin:auto;padding:20px}h1{margin:0 0 6px;font-size:24px}p.note{margin:0 0 14px;color:#61716b;font-size:14px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:12px}input{font:inherit;padding:8px 10px;border:1px solid #d7ddd1;border-radius:6px;min-width:220px}button{font:inherit;padding:7px 12px;border:1px solid #d7ddd1;border-radius:6px;background:#faf9f4;cursor:pointer}button[aria-pressed=true]{background:#243a3a;color:#f2f1eb;border-color:#243a3a}
table{width:100%;border-collapse:collapse;background:#faf9f4}th,td{padding:8px 10px;border:1px solid #d7ddd1;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#edf0e6;position:sticky;top:0}td.z{font-size:24px;text-align:center;width:56px}td.n{text-align:right;width:64px;color:#61716b}td.c{white-space:nowrap;color:#61716b;font-size:14px}td.why{font-size:13px;color:#61716b}
mark{background:#ffe9a8}@media(max-width:600px){main{padding:10px}th,td{padding:6px}td.z{font-size:20px}}</style></head>
<body><main><h1>人工规定的拆分</h1><p class="note">55 全部拆分对照中标"人工校对"的 __N__ 字，按字频排。"1.0 人工定"是本体；"第十九批·正"是 一＋止→正 的合并；"根集变动"是删根加根的机械结果。现行拆分与 1.0 不同时用底色标出。</p>
<div class="bar"><input id="q" placeholder="输入字、部件或拆分筛选"><span id="tabs"></span><span id="count"></span></div>
<table><thead><tr><th>字</th><th>字频</th><th>现行拆分</th><th>1.0 拆分</th><th>类别</th><th>依据</th></tr></thead><tbody id="out"></tbody></table></main>
<script>const rows=__DATA__;const cats=__CATS__;let cat='全部';const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const q=document.querySelector('#q'),out=document.querySelector('#out'),tabs=document.querySelector('#tabs');
function render(){const t=q.value.trim();const a=rows.filter(r=>(cat==='全部'||r.类===cat)&&(!t||r.字===t||r.现.includes(t)||r.旧.includes(t)||r.据.includes(t)));
out.innerHTML=a.map(r=>`<tr><td class="z">${esc(r.字)}</td><td class="n">${r.频||'—'}</td><td>${r.现!==r.旧?'<mark>'+esc(r.现)+'</mark>':esc(r.现)}</td><td>${esc(r.旧)}</td><td class="c">${esc(r.类)}</td><td class="why">${esc(r.据)}</td></tr>`).join('');document.querySelector('#count').textContent='共 '+a.length+' 字';}
tabs.innerHTML=['全部',...Object.keys(cats)].map(c=>`<button type="button" data-c="${esc(c)}" aria-pressed="${c===cat}">${esc(c)}${cats[c]?' '+cats[c]:''}</button>`).join('');
tabs.querySelectorAll('button').forEach(b=>b.onclick=()=>{cat=b.dataset.c;tabs.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));render();});q.oninput=render;render();</script></body></html>'''
page = page.replace('__N__', str(len(rows))).replace('__DATA__', data).replace('__CATS__', json.dumps(counts, ensure_ascii=False))
open(H + '/人工规定拆分清单.html', 'w', encoding='utf-8').write(page)
print('已生成', len(rows), '字，分类', counts)
