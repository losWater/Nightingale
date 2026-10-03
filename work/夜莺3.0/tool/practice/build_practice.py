"""夜莺 3.0（NB46）临时字根练习：以夜莺 2.0 离线工具包的字根练习页为底，换成 NB46 键位。
- 根集合：3.0 根组（= 2.5，去掉已无字使用的“鱼省”，补上 2.5 新增的“戈无点”）。
- 模式：归并组 / 全部根形，各分“全部”和“只练改动过的根”（键位与 2.0 不同的根；2.0 与 2.5 键位相同）。
- 进度单独存（nightingale30_nb46_memory_v1），不影响 2.0 练习的进度。
用法：python tool/practice/build_practice.py [布局json] [输出html]
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRC = Path.home() / 'Nightingale/work/夜莺2.0/65_群友离线工具包/夜莺2.0离线工具包/字根练习.html'
layout = json.load(open(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'release/NB46_layout.json', encoding='utf-8'))
out = Path(sys.argv[2] if len(sys.argv) > 2 else Path.home() / 'Downloads/夜莺3.0_NB46_字根练习.html')
meta = json.load(open(ROOT / 'build/out/n30/meta.json', encoding='utf-8'))
splits = json.load(open(ROOT / 'data/baseline/splits.json', encoding='utf-8'))
g_of = {r: g for g, rs in meta['groups'].items() for r in rs}

t = SRC.read_text(encoding='utf-8')


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
    if r == '戈':
        g = g_of['戈无点']
        new_roots.append({'根': '戈无点', '键': layout[g], '原键': meta['layout'][g], '组': x['组'], '例字': '尧、晓、烧、浇、挠'})
missing = set(g_of) - {x['根'] for x in new_roots}
assert not missing, missing
put('roots', new_roots)

# 戈无点例字：常用字在前
ex, _, _ = literal('rootExamples')
order = ['尧', '晓', '烧', '浇', '挠', '侥', '娆', '峣', '桡', '哓']
lst = [{'字': c, '位置': '首根' if splits[c][0][0] == '戈无点' else '末根', '拆分': ' ＋ '.join(p[0] for p in splits[c])} for c in order if c in splits]
ex['戈无点'] = {'1': lst[:1], '2': lst[:2], '4': lst[:4]}
put('rootExamples', ex)

# ---- 标题与说明 ----
rep('<title>夜莺2.0字根记忆练习</title>', '<title>夜莺3.0（NB46）字根练习</title>')
rep('<h1>夜莺2.0字根记忆练习</h1>', '<h1>夜莺3.0（NB46）字根记忆练习 · 临时版</h1><p>键位为 3.0 候选方案 NB46。“只练改动过的根”只出键位与 2.0 不同的根，题目上会标出它在 2.0 的键位。</p>')
rep("STORAGE='nightingale20_memory_v1'", "STORAGE='nightingale30_nb46_memory_v1'")
rep('<option value="group">归并组练习</option><option value="all">全部根形练习（403个）</option>',
    '<option value="group">归并组练习</option><option value="group_changed">归并组练习（只练改动过的）</option>'
    '<option value="all">全部根形练习</option><option value="all_changed">全部根形练习（只练改动过的）</option>')
rep('两种模式独立保存', '各模式独立保存')
rep('导入会替换两种模式的进度', '导入会替换所有模式的进度')

# ---- 归并组带上 2.0 键位；“正”的键位跟随布局 ----
rep("return {根:name,键:items[0].键,原组:origin,", "return {根:name,键:items[0].键,原键:items[0].原键,原组:origin,")
zheng = next(x for x in new_roots if x['根'] == '正')
rep('grouped.push({根:"正",键:"s",', f'grouped.push({{根:"正",键:"{zheng["键"]}",原键:"{zheng["原键"]}",')

# ---- 四种模式 ----
rep("document.querySelector('#kind').options[0].textContent='归并组练习（'+grouped.length+'组）';\n"
    "document.querySelector('#kind').options[1].textContent='全部根形练习（'+roots.length+'根）';\n"
    "const decks={group:grouped,all:roots};",
    "const changed=x=>x.键!==x.原键;\n"
    "const decks={group:grouped,group_changed:grouped.filter(changed),all:roots,all_changed:roots.filter(changed)};\n"
    "const KINDS=Object.keys(decks),KIND_NAME={group:'归并组',group_changed:'归并组（改动）',all:'全部根形',all_changed:'全部根形（改动）'};\n"
    "const KIND_LABEL={group:'归并组练习',group_changed:'归并组练习 · 只练改动过的',all:'全部根形练习',all_changed:'全部根形练习 · 只练改动过的'};\n"
    "for(const o of document.querySelector('#kind').options)o.textContent=KIND_LABEL[o.value]+'（'+decks[o.value].length+(o.value.startsWith('group')?'组':'根')+'）';")
rep("for(const k of ['group','all'])saved[k]=upgradeAppend(saved[k],k);", "for(const k of KINDS)saved[k]=upgradeAppend(saved[k],k);")
rep("progress:{group:saved.group,all:saved.all}}", "progress:Object.fromEntries(KINDS.map(k=>[k,saved[k]]))}")
rep("!['group','all'].includes(p.mode)", "!KINDS.includes(p.mode)")
rep(" for(const k of ['group','all']){const s=upgradeAppend(p.progress[k],k);", " for(const k of KINDS){const s=upgradeAppend(p.progress[k],k);")
rep("const summary=['group','all'].map(k=>(k==='group'?'归并组':'全部根形')+", "const summary=KINDS.map(k=>KIND_NAME[k]+")
rep("format:'nightingale-root-practice'", "format:'nightingale30-nb46-root-practice'")
rep("p.format!=='nightingale-root-practice'", "p.format!=='nightingale30-nb46-root-practice'")
rep("a.download='夜莺字根练习进度_'", "a.download='夜莺3.0_NB46字根练习进度_'")
rep("'已导出两种模式的进度文件", "'已导出所有模式的进度文件")
rep("将替换当前两种模式的进度", "将替换当前所有模式的进度")

# ---- 题目上标出 2.0 键位 ----
rep("$('#members').textContent=active&&x.成员?'归并组：'+rootLabel(x.根):'';",
    "$('#members').textContent=(active&&x.成员?'归并组：'+rootLabel(x.根):'')+(active&&x.原键&&x.键!==x.原键?(x.成员?'　·　':'')+'2.0 在 '+x.原键.toUpperCase()+' 键，3.0 搬家了':'');")

out.write_text(t, encoding='utf-8')
n = len(new_roots); c = sum(1 for x in new_roots if x['键'] != x['原键'])
print(out, '根形', n, '改动', c)
