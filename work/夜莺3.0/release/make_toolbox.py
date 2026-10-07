"""夜莺 3.0 啾啾工具箱：以夜莺 2.5 的 资料/拆分原本.html 为底，六个视图全部换成 3.0（NB46）数据。
- 拆分查询 / 部件反查：D（拆分、根键位、单字编码与同码字）、ROOTS（NB46 键位；去掉鱼省，补上夭、父）
- 字根练习：tool/practice/build_practice.py 的输出
- 字根表：键位换成 NB46，按新键位排列（同键内保持 2.5 的根族顺序）；例字只留 3.0 拆分里仍含该根的，不足 4 个按字频补
- 字根图：release/夜莺3.0_NB46_字根图.html（不标原键的干净版；与 2.5 字根图同一模板）
- 完整拆分表：3.0 拆分
另外把每个视图单独存成一页，放在输出目录的“单页”里，可单独离线打开。
用法：python release/make_toolbox.py [输出目录]   # 默认 ~/Downloads/夜莺3.0_工具箱
"""
import collections, json, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
N25 = Path.home() / 'Nightingale/夜莺2.5'
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / 'Downloads/夜莺3.0_工具箱'
SINGLE = ROOT / 'release/tables/夜莺3.0_NB46_字词表.txt'      # 单字编码（含彩蛋码、容错码）取自字词表
PLAIN = ROOT / 'release/tables/夜莺3.0_NB46_普通单字表.txt'


def locate(text, name):
    m = re.search(r'\b(?:const|let)\s+' + name + r'\s*=\s*', text)
    val, end = json.JSONDecoder().raw_decode(text[m.end():])
    return val, m.end(), m.end() + end


def put(text, name, value):
    _, a, b = locate(text, name)
    return text[:a] + json.dumps(value, ensure_ascii=False) + text[b:]


def rep(text, old, new, count=1):
    assert text.count(old) == count, (old[:60], text.count(old))
    return text.replace(old, new)


def rd(p): return [tuple(l.rstrip('\r\n').split('\t')[:2]) for l in open(p, encoding='utf-8-sig') if '\t' in l]


page = (N25 / '资料/拆分原本.html').read_text(encoding='utf-8-sig')
views, va, vb = locate(page, 'views')
splits = json.load(open(ROOT / 'data/baseline/splits.json', encoding='utf-8'))
meta = json.load(open(ROOT / 'build/out/n30/meta.json', encoding='utf-8'))
layout = json.load(open(ROOT / 'release/NB46_layout.json', encoding='utf-8'))
g_of = {r: g for g, rs in meta['groups'].items() for r in rs}
key = lambda r: layout[g_of[r]]
names = lambda c: [p[0] for p in splits.get(c, [])]

# ---- 单字编码：同码按 3.0 普通单字表序，彩蛋码/容错码随后（与 Rime 包的单字表一致）----
sym = set(rd(N25 / '主表/符号表.txt'))
plain = [r for r in rd(PLAIN) if r not in sym]
pos = set(plain)
special = [r for r in rd(SINGLE) if len(r[0]) == 1 and r not in pos]
slots = collections.defaultdict(list)
for t, c in plain + special: slots[c].append(t)
codes_of = collections.defaultdict(list)
for c, ts in slots.items():
    for t in ts: codes_of[t].append(c)

# ---- 拆分查询 / 部件反查 ----
q25 = views['query']
D, _, _ = locate(q25, 'D')
ROOTS, _, _ = locate(q25, 'ROOTS')
fam = {r['根']: r['组'] for r in ROOTS}
fam['夭'] = fam['天']; fam['父'] = fam['母']
roots3 = []
for r in ROOTS:
    if r['根'] not in g_of: continue                      # 鱼省：2.5 起已无字使用
    roots3.append(dict(r, 键=key(r['根'])))
    if r['根'] == '天': roots3.append({'根': '夭', '键': key('夭'), '组': fam['夭']})
    if r['根'] == '毌': roots3.append({'根': '父', '键': key('父'), '组': fam['父']})
assert {r['根'] for r in roots3} == set(g_of), set(g_of) ^ {r['根'] for r in roots3}
changed = 0
for ch, e in D.items():
    ns = names(ch)
    new = ' ＋ '.join(ns)
    changed += new != e['新拆']
    e['新拆'] = new
    e['根'] = [{'根': r, '键': key(r), '组': fam.get(r, r)} for r in ns]
    e['编码'] = [{'码': c, '位': slots[c].index(ch) + 1, '同码': slots[c]} for c in sorted(codes_of[ch], key=lambda c: (len(c), c))]
    assert e['编码'], ch
missing = set(splits) - set(D)
assert not missing, ''.join(sorted(missing))[:50]


def query_view(text):
    text = put(put(text, 'ROOTS', roots3), 'D', D)
    text = rep(text, '<p class="muted">夜莺2.0</p>', '<p class="muted">夜莺3.0</p>')
    text = rep(text, '显示当前2.0单字编码', '显示当前3.0单字编码')
    text = rep(text, '覆盖8105字', f'覆盖{len(D)}字（含通用规范汉字表 8105 字）')
    return re.sub(r'<title>夜莺2\.0', '<title>夜莺3.0', text)


views['query'] = query_view(views['query'])
views['components'] = query_view(views['components'])

# ---- 完整拆分表 ----
t = views['text']
rows, _, _ = locate(t, 'rows')
rows = [[c, ' ＋ '.join(names(c)), names(c)[0], names(c)[-1]] for c, *_ in rows]
views['text'] = put(t, 'rows', rows)

# ---- 字根表 ----
rank = sorted(D, key=lambda c: D[c]['排名'] or 9e9)
has = collections.defaultdict(list)                      # 根 → 含该根的字（按字频）
for c in rank:
    for r in dict.fromkeys(names(c)): has[r].append(c)
t = views['roots']
body_re = re.compile(r'<tr><td>([^<]*)</td><td>(.*?)</td><td>([^<]*)</td><td>([^<]*)</td></tr>')
old = body_re.findall(t)


def examples(rs, given):
    keep = [c for c in given.split('、') if c and any(r in names(c) for r in rs)]
    for r in rs:
        for c in has[r]:
            if len(keep) >= 4: break
            if c not in keep: keep.append(c)
    return '、'.join(keep[:4])


new_rows = []
for k, cell, family, ex in old:
    rs = [{'班（字架）': '玨'}.get(x, x) for x in re.sub(r'<[^>]+>', '', cell).split('、')]   # 页面显示名 → 根名
    if rs[0] not in g_of: continue
    new_rows.append((key(rs[0]), cell, family, examples(rs, ex)))
    if rs[0] == '天': new_rows.append((key('夭'), '夭', fam['夭'], examples(['夭'], '笑、跃、沃、妖')))
    if rs[0] == '毌': new_rows.append((key('父'), '父', fam['父'], examples(['父'], '父、爸、交、校')))
new_rows.sort(key=lambda x: x[0])                        # 稳定排序：同键内保持 2.5 顺序（根族连在一起）
a, b = t.index('<tbody>') + 7, t.index('</tbody>')
t = t[:a] + ''.join(f'<tr><td>{k}</td><td>{c}</td><td>{f}</td><td>{x}</td></tr>' for k, c, f, x in new_rows) + t[b:]
t = rep(t, '夜莺2.0字根总表', '夜莺3.0字根总表', 2)
t = rep(t, '使用当前人工裁定布局。', '使用 3.0 的 NB46 布局。')
views['roots'] = t

# ---- 字根图 ----
views['image'] = (ROOT / 'release/夜莺3.0_NB46_字根图.html').read_text(encoding='utf-8-sig')

# ---- 字根练习 ----
prac = ROOT.parent / '.cache/yeying-toolbox-practice.html'
subprocess.run([sys.executable, str(ROOT / 'tool/practice/build_practice.py'), str(ROOT / 'release/NB46_layout.json'), str(prac)], check=True)
views['practice'] = prac.read_text(encoding='utf-8')
prac.unlink()

for k, v in views.items():
    assert not re.search(r'夜莺\s*2\.[05]', v), (k, re.search(r'.{20}夜莺\s*2\.[05].{20}', v).group())
html = page[:va] + json.dumps(views, ensure_ascii=False).replace('<', '\\u003c') + page[vb:]   # 同 2.5：内嵌页面里的 </script> 不能截断外层脚本
OUT.mkdir(parents=True, exist_ok=True)
(OUT / '夜莺啾啾工具箱.html').write_text(html, encoding='utf-8')
LABEL = {'query': '拆分查询', 'components': '部件反查', 'practice': '字根练习', 'roots': '字根表', 'image': '字根图', 'text': '完整拆分表'}
(OUT / '单页').mkdir(exist_ok=True)
for k, v in views.items():
    (OUT / '单页' / f'夜莺3.0_{LABEL[k]}.html').write_text(v, encoding='utf-8')
print(OUT, '拆分改', changed, '字；ROOTS', len(roots3), '；字根表', len(new_rows), '行；拆分表', len(rows), '字')
