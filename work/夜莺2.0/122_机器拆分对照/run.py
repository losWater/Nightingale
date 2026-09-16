# -*- coding: utf-8 -*-
"""实验（2026-09-16 你提议）：用 2.0 根集、去掉所有人工拆分规则，让 Chai 自己机器拆一遍 8105 字，和现行 2.0 拆分表逐字对照。
- 根集：54/frozen/当前完整根表.json 的 133 组根形 ID（+ 第十九批 正 归 止组）→ Chai config 的 form.mapping（组内首根形为宿主）。
- 分析基线：重开工程/04_Chai输入/结构分析基线_待审计.yaml（只保留字形数据与分析器设置，customize 清空 = 无人工规则）。
- 运行器：重开工程/scripts/chai_split_runner.ts（bun）。
- 对照：55/当前完整拆分_根ID.json（现行 2.0，含继承的人工规则）。差异分"人工校对字 / 非人工字"，并标首末根是否变化（影响编码）。"""
import io, sys, os, json, subprocess, datetime, collections, importlib.util, copy
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import yaml
E = 'E:/夜莺2.0'; W = E + '/work/夜莺2.0'; R = E + '/work/重开工程'; H = os.path.dirname(os.path.abspath(__file__))
J = lambda p: json.load(open(p, encoding='utf-8-sig'))
spec = importlib.util.spec_from_file_location('audit', R + '/scripts/audit_manual_split_propagation.py'); audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
baseline = yaml.safe_load(open(R + '/04_Chai输入/结构分析基线_待审计.yaml', encoding='utf-8'))
by_name, labels = audit.repertoire_maps(baseline)
# 2.0 根集 → mapping
groups = J(W + '/54_补删鹿旁保留羊南心四起点试跑/frozen/当前完整根表.json')['根组']
disp = {}
for g in groups:
    for i, d in zip(g['根形ID'], g['根形']): disp[i] = d
if '正' not in disp:
    for g in groups:
        if '止' in g['根形ID']: g['根形ID'].append('正'); g['根形'].append('正'); disp['正'] = '正'
mapping = {}; KEYS = audit.KEYS
for n, g in enumerate(groups):
    ids = g['根形ID']; head = ids[0]
    mapping[head] = KEYS[n % 26]
    for i in ids[1:]: mapping[i] = {'element': head}
mapping['6'] = {'element': '5'}
cfg = copy.deepcopy(baseline)
cfg.setdefault('form', {})['mapping'] = mapping; cfg['form']['mapping_space'] = {}; cfg['form']['alphabet'] = KEYS
cfg.setdefault('analysis', {})['customize'] = {}; cfg['analysis']['dynamic_customize'] = {}
cfg['info'] = {'name': '夜莺2.0机器拆分对照', 'author': 'nightingale', 'version': 'exp-122', 'description': '2.0 roots, no manual rules; experiment only'}
cur = J(W + '/55_拆分继承核验/当前完整拆分_根ID.json'); charset = sorted(cur)
run_dir = H + '/run_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'); os.makedirs(run_dir, exist_ok=True)
# 根 ID 是否都在字库里（PUA 部件需在基线 repertoire 或 Chai 内置字库）
known = set(by_name.values()) | set(labels) | {str(i) for i in range(1, 7)}
print('根形 %d，宿主 %d' % (len(mapping) - 1, len(groups)))
audit.ROOT = audit.ROOT  # 运行目录
rows_raw = audit.invoke('AUTO_2.0', cfg, charset, __import__('pathlib').Path(run_dir))
# 输出 token → 2.0 根 ID
S = {v: k for k, v in audit.STROKES.items()}
def tok(t):
    if t == '6': return '5'
    if t in audit.STROKES: return audit.STROKES[t]
    if t in by_name: return by_name[t]
    return t
gid = {}
for g in groups:
    for i in g['根形ID']: gid[i] = g['根形ID'][0]
G = lambda ids: [gid.get(i, i) for i in ids]
auto = {c: [tok(t) for t in seq] for c, seq in rows_raw.items()}
manual = {r['字'] for r in J(W + '/55_拆分继承核验/全部拆分对照.json') if r.get('人工校对')}
rank = {r['字']: r['新排名'] for r in J(W + '/32_多来源字频重建/试验整字频率.json')['字表']}
show = lambda ids: ' ＋ '.join(disp.get(i, S.get(i, i)) for i in ids)
diffs = []
for c in charset:
    a, b = cur[c], auto.get(c)
    if b is None: diffs.append({'字': c, '类': '机器无结果'}); continue
    if a == b: continue
    ga, gb = G(a), G(b)
    if ga == gb: cat = '同组根形之差'          # 每个位置根组相同，只是根形写法不同（横/一、竖/丨）：编码不受影响
    elif ga[0] == gb[0] and ga[-1] == gb[-1]: cat = '内部不同'   # 首末根组相同，中间不同：编码不受影响
    else: cat = '首末根变'                         # 影响编码
    diffs.append({'字': c, '频': rank.get(c, 0), '现行': show(a), '机器': show(b), '人工': c in manual, '类': cat, '首末变': cat == '首末根变',
                  '首末现': show([a[0], a[-1]]), '首末机': show([b[0], b[-1]])})
diffs.sort(key=lambda d: d.get('频') or 99999)
real = [d for d in diffs if d.get('类') != '同组根形之差']
stat = {'字数': len(charset), '不一致(含同组根形之差)': len(diffs), '同组根形之差(不影响编码)': len(diffs) - len(real), '实质不一致': len(real),
        '实质不一致中人工校对字': sum(1 for d in real if d.get('人工')), '实质不一致中非人工字': sum(1 for d in real if not d.get('人工')),
        '首末根有变(影响编码)': sum(1 for d in diffs if d.get('首末变')), '仅内部不同': sum(1 for d in diffs if d.get('类') == '内部不同'),
        '其中人工校对字': sum(1 for d in diffs if d.get('人工')), '非人工字': sum(1 for d in diffs if not d.get('人工')),
        '人工校对字总数': len(manual), '人工校对字中机器一致': len(manual) - sum(1 for d in diffs if d.get('人工')),
        '不一致里前1500字': sum(1 for d in diffs if 0 < (d.get('频') or 0) <= 1500), '不一致里前3000字': sum(1 for d in diffs if 0 < (d.get('频') or 0) <= 3000)}
json.dump({'统计': stat, '差异': diffs, '运行目录': run_dir}, open(H + '/对照结果.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
# HTML
import html as _h
data = json.dumps(diffs, ensure_ascii=False).replace('<', '\\u003c')
page = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>机器拆分对照 · 夜莺2.0</title>
<style>*{box-sizing:border-box}body{margin:0;background:#f2f1eb;color:#243a3a;font:17px/1.6 "Microsoft YaHei",sans-serif}main{max-width:1200px;margin:auto;padding:20px}h1{margin:0 0 6px;font-size:24px}p.note{margin:0 0 14px;color:#61716b;font-size:14px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:12px}input{font:inherit;padding:8px 10px;border:1px solid #d7ddd1;border-radius:6px;min-width:220px}button{font:inherit;padding:7px 12px;border:1px solid #d7ddd1;border-radius:6px;background:#faf9f4;cursor:pointer}button[aria-pressed=true]{background:#243a3a;color:#f2f1eb;border-color:#243a3a}
table{width:100%;border-collapse:collapse;background:#faf9f4}th,td{padding:8px 10px;border:1px solid #d7ddd1;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#edf0e6;position:sticky;top:0}td.z{font-size:24px;text-align:center;width:56px}td.n{text-align:right;width:64px;color:#61716b}td.c{white-space:nowrap;color:#61716b;font-size:14px}
mark{background:#ffe9a8}.fe{color:#8a2d2d;font-weight:600}@media(max-width:600px){main{padding:10px}th,td{padding:6px}td.z{font-size:20px}}</style></head>
<body><main><h1>机器拆分对照</h1><p class="note">__STAT__</p>
<div class="bar"><input id="q" placeholder="输入字或部件筛选"><span id="tabs"></span><span id="count"></span></div>
<table><thead><tr><th>字</th><th>字频</th><th>现行拆分（2.0）</th><th>机器拆分（无人工规则）</th><th>类别</th><th>首末根</th><th>人工校对</th></tr></thead><tbody id="out"></tbody></table></main>
<script>const rows=__DATA__;let f='全部';const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const q=document.querySelector('#q'),out=document.querySelector('#out'),tabs=document.querySelector('#tabs');
const filters={'全部':r=>true,'首末根变':r=>r.类==='首末根变','内部不同':r=>r.类==='内部不同','同组根形之差':r=>r.类==='同组根形之差','人工校对字':r=>r.人工,'非人工字':r=>!r.人工,'前3000字':r=>r.频>0&&r.频<=3000};
function render(){const t=q.value.trim();const a=rows.filter(r=>filters[f](r)&&(!t||r.字===t||(r.现行||'').includes(t)||(r.机器||'').includes(t)));
out.innerHTML=a.map(r=>`<tr><td class="z">${esc(r.字)}</td><td class="n">${r.频||'—'}</td><td>${esc(r.现行||'')}</td><td><mark>${esc(r.机器||r.类||'')}</mark></td><td class="c">${esc(r.类||'')}</td><td class="c">${r.首末变?'<span class="fe">'+esc(r.首末现)+' → '+esc(r.首末机)+'</span>':'不变'}</td><td class="c">${r.人工?'是':''}</td></tr>`).join('');document.querySelector('#count').textContent='共 '+a.length+' 字';}
tabs.innerHTML=Object.keys(filters).map(c=>`<button type="button" data-c="${esc(c)}" aria-pressed="${c===f}">${esc(c)} ${rows.filter(filters[c]).length}</button>`).join('');
tabs.querySelectorAll('button').forEach(b=>b.onclick=()=>{f=b.dataset.c;tabs.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));render();});q.oninput=render;render();</script></body></html>'''
statline = '8105 字中机器拆分与现行不一致 %d 字，其中同组根形之差（横/一 等，不影响编码）%d，实质不一致 %d（首末根变 %d、内部不同 %d）；实质不一致里人工校对字 %d、非人工字 %d。运行目录 %s' % (
    stat['不一致(含同组根形之差)'], stat['同组根形之差(不影响编码)'], stat['实质不一致'], stat['首末根有变(影响编码)'], stat['仅内部不同'], stat['实质不一致中人工校对字'], stat['实质不一致中非人工字'], os.path.basename(run_dir))
open(H + '/对照结果.html', 'w', encoding='utf-8').write(page.replace('__STAT__', _h.escape(statline)).replace('__DATA__', data))
print(json.dumps(stat, ensure_ascii=False, indent=1))
print('样例:', [(d['字'], d.get('现行'), d.get('机器')) for d in diffs[:8]])
