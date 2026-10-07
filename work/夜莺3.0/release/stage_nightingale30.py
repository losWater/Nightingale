"""在独立目录搭一个“夜莺仓库”结构，放入 夜莺3.0 维护目录，供夜莺仓库的构建工具（tools/maintenance/build_mac.py --root）使用。
正式夜莺仓库不动：tools、assets、.cache 用符号链接指向 ~/Nightingale。
夜莺3.0/
  主表：单字表（3.0 普通单字表去符号 + 彩蛋码/容错码）、字词表（release/make_ciku.py）、符号表与快符（沿用 2.5）
  配置：编码类型（3.0 的彩蛋码、容错码）、单字版差异与词语读音（空，同 2.5）
  资料/拆分原本.html：以 2.5 为底，拆分查询数据 D 换成 3.0 的拆分、键位（NB46）、编码；其他视图仍是 2.5 的（待另行更新）
用法：python release/stage_nightingale30.py [搭台目录]
"""
import collections, json, re, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
NG = Path.home() / 'Nightingale'; N25 = NG / '夜莺2.5'
STAGE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / '.cache/yeying30-build'
V = STAGE / '夜莺3.0'


def rd(p): return [tuple(l.rstrip('\r\n').split('\t')[:2]) for l in open(p, encoding='utf-8-sig') if '\t' in l]


def render(rows): return ''.join(f'{t}\t{c}\n' for t, c in rows)


STAGE.mkdir(parents=True, exist_ok=True)
for name in ('tools', 'assets'):
    link = STAGE / name
    if not link.exists(): link.symlink_to(NG / name)
(STAGE / '.cache').mkdir(exist_ok=True)
if not (STAGE / '.cache/rime').exists(): (STAGE / '.cache/rime').symlink_to(NG / '.cache/rime')
(STAGE / 'maintenance.json').write_text(json.dumps({'active': '夜莺3.0'}, ensure_ascii=False, indent=2) + '\n')
for d in ('主表', '配置', '资料', '记录', '产物', '备份'): (V / d).mkdir(parents=True, exist_ok=True)
(V / '版本.json').write_text(json.dumps({'version': '3.0', 'status': 'active', 'note': '夜莺 3.0（NB46）试构建，由 Yozakura release/stage_nightingale30.py 搭台；不是正式维护目录。'},
                                       ensure_ascii=False, indent=2) + '\n')

# ---- 主表 ----
ci = rd(ROOT / 'release/tables/夜莺3.0_NB46_字词表.txt')
sym = rd(N25 / '主表/符号表.txt'); symset = set(sym)
single = [(t, c) for t, c in ci if len(t) == 1]          # 字词表里的单字（含彩蛋码、容错码），候选序同字词表
plain = [r for r in rd(ROOT / 'release/tables/夜莺3.0_NB46_普通单字表.txt') if r not in symset]
pos = {r: i for i, r in enumerate(plain)}
special = [r for r in single if r not in pos]
by_code = collections.defaultdict(list)
for t, c in plain + special: by_code[c].append(t)
single = [(t, c) for c in sorted(by_code) for t in by_code[c]]   # 单字表：同码按 3.0 普通单字表序，特殊码随后
(V / '主表/单字表.txt').write_text(render(single), encoding='utf-8')
(V / '主表/字词表.txt').write_text(render(ci), encoding='utf-8')
shutil.copy(N25 / '主表/符号表.txt', V / '主表/符号表.txt')
shutil.copy(N25 / '主表/快符.txt', V / '主表/快符.txt')

# ---- 配置 ----
info = json.load(open(ROOT / 'release/tables/夜莺3.0_NB46_字词表_说明.json', encoding='utf-8'))
types = [{'text': t, 'code': c, 'type': k} for t, c, k in info['特殊码']]
(V / '配置/编码类型.json').write_text(json.dumps({'source': 'Yozakura release/make_ciku.py 特殊码（3.0）', 'entries': types},
                                              ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(V / '配置/单字版差异.json').write_text('[]\n'); (V / '配置/词语读音.json').write_text('{}\n')
for f in ('码表概念与规则.md', '评估规则.md'):
    shutil.copy(N25 / '资料' / f, V / '资料' / f)

# ---- 拆分原本：D 换成 3.0 ----
html = (N25 / '资料/拆分原本.html').read_text(encoding='utf-8-sig')


def locate(text, name):
    m = re.search(r'\b(?:const|let)\s+' + name + r'\s*=\s*', text)
    val, end = json.JSONDecoder().raw_decode(text[m.end():])
    return val, m.end(), m.end() + end


views, va, vb = locate(html, 'views')
query = views['query']
D, da, db = locate(query, 'D')
splits = json.load(open(ROOT / 'data/baseline/splits.json', encoding='utf-8'))
meta = json.load(open(ROOT / 'build/out/n30/meta.json', encoding='utf-8'))
layout = json.load(open(ROOT / 'release/NB46_layout.json', encoding='utf-8'))
g_of = {r: g for g, rs in meta['groups'].items() for r in rs}
fam = {}                                                  # 根 → 2.5 的“组”名（根族）
for e in D.values():
    for r in e['根']: fam.setdefault(r['根'], r['组'])
fam.setdefault('夭', fam['天']); fam.setdefault('父', fam['母'])
slots = collections.defaultdict(list)
for t, c in single: slots[c].append(t)
codes_of = collections.defaultdict(list)
for t, c in single: codes_of[t].append(c)
changed = 0
for ch, e in D.items():
    rs = splits[ch]
    new = ' ＋ '.join(r[0] for r in rs)
    if new != e['新拆']: changed += 1
    e['新拆'] = new
    e['根'] = [{'根': r[0], '键': layout[g_of[r[0]]], '组': fam.get(r[0], r[0])} for r in rs]
    e['编码'] = [{'码': c, '位': slots[c].index(ch) + 1, '同码': slots[c]} for c in sorted(codes_of[ch], key=lambda c: (len(c), c))]
query = query[:da] + json.dumps(D, ensure_ascii=False) + query[db:]
views['query'] = query
html = html[:va] + json.dumps(views, ensure_ascii=False) + html[vb:]
(V / '资料/拆分原本.html').write_text(html, encoding='utf-8')
print('搭台', STAGE, '；单字表', len(single), '字词表', len(ci), '；特殊码', len(types), '；拆分改', changed, '字')
