"""夜莺 3.0 字根练习：以夜莺 2.5 啾啾工具箱里的字根练习页为底（也可指定其他来源），换成 3.0（NB46）键位。
- 根集合：3.0 根组（= 2.5，去掉已无字使用的“鱼省”，补上 2.5 新增的“戈无点”、3.0 新增的“夭”〔归入天组〕、“父”〔归入母组〕，原键留空＝新根）。
- 模式：归并组 / 全部根形，各分“全部”和“只练改动过的根”（键位与 2.0 不同的根；2.0 与 2.5 键位相同）。
- 全部例字的拆分刷新为 3.0（夭、父等），不再含该根的例字去掉。
- 进度单独存（nightingale_memory_v1，不带版本号），不影响 2.x 练习的进度。
用法：python tool/practice/build_practice.py [布局json] [输出html] [来源html]（来源默认取 2.5 拆分原本里的练习视图）
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
layout = json.load(open(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'release/NB46_layout.json', encoding='utf-8'))
out = Path(sys.argv[2] if len(sys.argv) > 2 else Path.home() / 'Downloads/夜莺3.0_字根练习.html')
if len(sys.argv) > 3:
    t = Path(sys.argv[3]).read_text(encoding='utf-8')
else:
    _page = (Path.home() / 'Nightingale/夜莺2.5/资料/拆分原本.html').read_text(encoding='utf-8-sig')
    _m = re.search(r'\b(?:const|let)\s+views\s*=\s*', _page)
    t = json.JSONDecoder().raw_decode(_page[_m.end():])[0]['practice']
meta = json.load(open(ROOT / 'build/out/n30/meta.json', encoding='utf-8'))
splits = json.load(open(ROOT / 'data/baseline/splits.json', encoding='utf-8'))
g_of = {r: g for g, rs in meta['groups'].items() for r in rs}



def literal(name):
    m = re.search(r'\bconst ' + name + r'\s*=\s*', t)
    v, end = json.JSONDecoder().raw_decode(t[m.end():])
    return v, m.end(), m.end() + end


def put(name, value):
    global t
    _, a, b = literal(name)
    t = t[:a] + json.dumps(value, ensure_ascii=False) + t[b:]


def rep(old, new, count=1):
    global t
    assert t.count(old) == count, (old[:60], t.count(old))
    t = t.replace(old, new)


# ---- 字根：NB46 键位，记下 2.0 键位 ----
roots, _, _ = literal('roots')
new_roots = []
for x in roots:
    r = x['根']
    if r not in g_of:
        continue                                   # 鱼省：2.5 起已无字使用
    new_roots.append(dict(x, 键=layout[g_of[r]], 原键=x['键']))
    if r == '戈' and not any(y['根'] == '戈无点' for y in roots):
        g = g_of['戈无点']
        new_roots.append({'根': '戈无点', '键': layout[g], '原键': meta['layout'][g], '组': x['组'], '例字': '尧、晓、烧、浇、挠'})
    if r == '天':
        new_roots.append({'根': '夭', '键': layout[g_of['夭']], '原键': '', '组': x['组'], '例字': '笑、跃、沃、妖、夭'})
    if r == '毌':
        new_roots.append({'根': '父', '键': layout[g_of['父']], '原键': '', '组': x['组'], '例字': '父、爸、交、校、爷'})
missing = set(g_of) - {x['根'] for x in new_roots}
assert not missing, missing
put('roots', new_roots)

# 戈无点例字：常用字在前
ex, _, _ = literal('rootExamples')
order = ['尧', '晓', '烧', '浇', '挠', '侥', '娆', '峣', '桡', '哓']
lst = [{'字': c, '位置': '首根' if splits[c][0][0] == '戈无点' else '末根', '拆分': ' ＋ '.join(p[0] for p in splits[c])} for c in order if c in splits]
ex['戈无点'] = {'1': lst[:1], '2': lst[:2], '4': lst[:4]}
lst = [{'字': c, '位置': '首末' if len(splits[c]) == 1 else ('首根' if splits[c][0][0] == '夭' else '末根'),
        '拆分': ' ＋ '.join(p[0] for p in splits[c])} for c in ['笑', '跃', '沃', '妖', '袄', '夭'] if c in splits]
ex['夭'] = {'1': lst[:1], '2': lst[:2], '4': lst[:4]}
lst = [{'字': c, '位置': '首末' if len(splits[c]) == 1 else ('首根' if splits[c][0][0] == '父' else '末根'),
        '拆分': ' ＋ '.join(p[0] for p in splits[c])} for c in ['爸', '交', '爷', '校', '父', '较'] if c in splits]
ex['父'] = {'1': lst[:1], '2': lst[:2], '4': lst[:4]}
# 全部例字刷新为 3.0 拆分：不再含该根的去掉，拆分与首末位置按 3.0
names = lambda c: [p[0] for p in splits.get(c, [])]
for r, levels in ex.items():
    for lv, items in levels.items():
        kept = []
        for it in items:
            ns = names(it['字'])
            if r not in ns: continue
            it['拆分'] = ' ＋ '.join(ns)
            it['位置'] = '首末' if len(ns) == 1 else '首根' if ns[0] == r else '末根' if ns[-1] == r else '中间根'
            kept.append(it)
        levels[lv] = kept
put('rootExamples', ex)
rs, _, _ = literal('roots')
for x in rs:
    if x.get('例字'):
        x['例字'] = '、'.join(c for c in x['例字'].split('、') if x['根'] in names(c))
put('roots', rs)

# 夭并入“大”那一部分（2.0 练习页按部分出归并组卡片）
parts, _, _ = literal('familyPartitions')
for part in parts.get('大／小', []):
    if part[0] == '大' and '夭' not in part[1].split(): part[1] += ' 夭'
put('familyPartitions', parts)

# ---- 标题与说明 ----
rep('<title>夜莺2.0字根记忆练习</title>', '<title>夜莺3.0字根记忆练习</title>')
rep('<h1>夜莺2.0字根记忆练习</h1>', '<h1>夜莺3.0字根记忆练习</h1><p>“只练改动过的根”只出键位与 2.x 不同的根和 3.0 新增的根（夭、父）；归并组模式里，新根所在的组（大、母）也算改动。题目上会标出它在 2.x 的键位或新增的根。</p>')
rep("STORAGE='nightingale20_memory_v1'", "STORAGE='nightingale_memory_v1'")
rep('<option value="group">归并组练习</option><option value="all">全部根形练习（403个）</option>',
    '<option value="group">归并组练习</option><option value="group_changed">归并组练习（只练改动过的）</option>'
    '<option value="all">全部根形练习</option><option value="all_changed">全部根形练习（只练改动过的）</option>')
rep('两种模式独立保存', '各模式独立保存')
rep('导入会替换两种模式的进度', '导入会替换所有模式的进度')

# ---- 归并组带上 2.0 键位；“正”的键位跟随布局 ----
rep("return {根:name,键:items[0].键,原组:origin,", "return {根:name,键:items[0].键,原键:items[0].原键,原组:origin,")
# 3.0 把 2.0 的同键归并组拆到不同键（如鸟 J、虫 M）：每个键只保留有字根的部分，归并提示只指同键的部分
rep("return parts.map(([name,members],partIndex)=>", "const live=parts.filter(([,m])=>items.some(x=>m.split(' ').includes(x.根)));\n return live.map(([name,members],partIndex)=>")
rep('归并提示:partIndex>0?parts[0][0]:""', '归并提示:partIndex>0?live[0][0]:""')
zheng = next(x for x in new_roots if x['根'] == '正')
rep('grouped.push({根:"正",键:"s",', f'grouped.push({{根:"正",键:"{zheng["键"]}",原键:"{zheng["原键"]}",')

# ---- 四种模式 ----
rep("document.querySelector('#kind').options[0].textContent='归并组练习（'+grouped.length+'组）';\n"
    "document.querySelector('#kind').options[1].textContent='全部根形练习（'+roots.length+'根）';\n"
    "const decks={group:grouped,all:roots};",
    "const NEW_ROOTS=new Set(roots.filter(r=>r.原键==='').map(r=>r.根));\n"
    "const newIn=x=>JSON.stringify(x.成员||[]).match(/[^\\[\\],\"]+/g)?.filter(m=>NEW_ROOTS.has(m))||[];\n"
    "const changed=x=>x.键!==x.原键||(x.成员&&newIn(x).length>0);   // 归并组：换了键，或组里有新根\n"
    "const decks={group:grouped,group_changed:grouped.filter(changed),all:roots,all_changed:roots.filter(changed)};\n"
    "const KINDS=Object.keys(decks),KIND_NAME={group:'归并组',group_changed:'归并组（改动）',all:'全部根形',all_changed:'全部根形（改动）'};\n"
    "const KIND_LABEL={group:'归并组练习',group_changed:'归并组练习 · 只练改动过的',all:'全部根形练习',all_changed:'全部根形练习 · 只练改动过的'};\n"
    "for(const o of document.querySelector('#kind').options)o.textContent=KIND_LABEL[o.value]+'（'+decks[o.value].length+(o.value.startsWith('group')?'组':'根')+'）';")
rep("for(const k of ['group','all'])saved[k]=upgradeAppend(saved[k],k);", "for(const k of KINDS)saved[k]=upgradeAppend(saved[k],k);")
rep("progress:{group:saved.group,all:saved.all}}", "progress:Object.fromEntries(KINDS.map(k=>[k,saved[k]]))}")
rep("!['group','all'].includes(p.mode)", "!KINDS.includes(p.mode)")
rep(" for(const k of ['group','all']){const s=upgradeAppend(p.progress[k],k);", " for(const k of KINDS){const s=upgradeAppend(p.progress[k],k);")
rep("const summary=['group','all'].map(k=>(k==='group'?'归并组':'全部根形')+", "const summary=KINDS.map(k=>KIND_NAME[k]+")
rep("'已导出两种模式的进度文件", "'已导出所有模式的进度文件")
rep("将替换当前两种模式的进度", "将替换当前所有模式的进度")

# ---- 题目上标出 2.0 键位 ----
rep("$('#members').textContent=active&&x.成员?'归并组：'+rootLabel(x.根):'';",
    "$('#members').textContent=(active&&x.成员?'归并组：'+rootLabel(x.根):'')+(active&&x.原键&&x.键!==x.原键?(x.成员?'　·　':'')+'2.x 在 '+x.原键.toUpperCase()+' 键，3.0 搬家了':'')+(active&&x.成员&&newIn(x).length?'　·　3.0 新增：'+newIn(x).join('、'):'');")

out.write_text(t, encoding='utf-8')
n = len(new_roots); c = sum(1 for x in new_roots if x['键'] != x['原键'])
print(out, '根形', n, '改动', c)
