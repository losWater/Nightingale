"""同一词库对比：夜莺普通单字表 vs 虎码秃版单字，都用虎码词库（tigress_ci）的二字词。
- 词频序：二字词按词库权重排序（同 eval/word_clash.top_words，夜莺门禁口径）。
- 夜莺词码：两字小鹤双拼（pypinyin 按词定音）；冲突 = 必须打全码的字音，全码 = 词码。
- 虎码词码：词库自带的码（不含 tigress_simp_ci 简词）；冲突 = 必须打全码的字（没有更短的码），全码 = 词码。
字档按夜桜字音基准字频：夜莺按字音，虎码按字（同字各读音相加），基准外的虎码字不计。
用法：.venv/bin/python release/clash_same_ci.py <夜莺普通单字表> [虎码目录]
"""
import collections, json, sys
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib')); sys.path.insert(0, str(ROOT / 'eval'))
from shuangpin import encode
from word_clash import top_words
L = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
E = yaml.load(open(ROOT / 'build/out/n30/elements.yaml', encoding='utf-8'), Loader=L)
META = json.load(open(ROOT / 'build/out/n30/meta.json', encoding='utf-8'))
N = sum(1 for e in E if e['拼音'] != 'reserved')
ONE = {(c, p) for c, p, n in json.load(open(ROOT / 'data/inputs/一二简.json', encoding='utf-8'))['fixed'] if n == 1}
TIGER = Path(sys.argv[2] if len(sys.argv) > 2 else Path.home() / 'Downloads/虎码秃版 鼠须管 （Mac）')

CB = ['前1500', '1500–3500', '3500–6000', '6000后']
WB = ['前1万', '1–3万', '3–6万', '6万后']
wband = lambda r: WB[0] if r <= 10000 else WB[1] if r <= 30000 else WB[2] if r <= 60000 else WB[3]

words = top_words('xiaohe', 10 ** 7)
wrank = {w: r for r, (w, _) in enumerate(words, 1)}


def show(title, grid, hit):
    print(f'\n{title}：冲突条数（涉及字/字音数）')
    print('\t'.join(['字档\\词档'] + WB + ['合计']))
    for cb in CB:
        print('\t'.join([cb] + [f'{grid[(cb, wb)]}({len(hit[(cb, wb)])})' for wb in WB] + [str(sum(grid[(cb, wb)] for wb in WB))]))
    print('\t'.join(['合计'] + [str(sum(grid[(cb, wb)] for cb in CB)) for wb in WB] + [str(sum(grid.values()))]))


# ---- 夜莺：按字音 ----
tiers = [(CB[0], set(META['tier_indices']['1500'])), (CB[1], set(META['tier_indices']['3500'])), (CB[2], set(META['tier_indices']['6000']))]
codes = collections.defaultdict(list)
for l in open(sys.argv[1], encoding='utf-8-sig'):
    p = l.rstrip('\n').split('\t')
    if len(p) >= 2 and len(p[0]) == 1:
        codes[p[0]].append(p[1])
by = collections.defaultdict(list)
for w, c in words:
    by[c].append(w)
grid, hit, top = collections.Counter(), collections.defaultdict(set), []
for i in range(N):
    ch, py = E[i]['词'], E[i]['拼音']
    sy = encode(py, 'xiaohe')
    mine = [c for c in codes[ch] if c[:2] == sy]
    if ((ch, py) in ONE and any(len(c) == 1 for c in codes[ch])) or any(len(c) < 4 for c in mine):
        continue
    full = next((c for c in mine if len(c) == 4), None)
    for w in by.get(full, ()):
        cb = next((n for n, s in tiers if i in s), CB[3]); wb = wband(wrank[w])
        grid[(cb, wb)] += 1; hit[(cb, wb)].add(i)
        if cb == CB[0] and wrank[w] <= 30000: top.append((ch, py, full, w, wrank[w]))
show('夜莺（' + Path(sys.argv[1]).stem + '）', grid, hit)
print('前1500 × 前3万：', sorted(top, key=lambda x: x[4]))


# ---- 虎码：按字 ----
def body(f):
    on = False
    for l in open(TIGER / f, encoding='utf-8'):
        if l.startswith('...'):
            on = True; continue
        if on and '\t' in l and not l.startswith('#'):
            yield l.rstrip('\n').split('\t')


cf = collections.Counter()
for i in range(N):
    if len(E[i]['词']) == 1: cf[E[i]['词']] += E[i]['频率']
crank = {c: r for r, (c, _) in enumerate(cf.most_common(), 1)}
cband = lambda r: CB[0] if r <= 1500 else CB[1] if r <= 3500 else CB[2] if r <= 6000 else CB[3]
tc = collections.defaultdict(set)
for p in body('tigress.dict.yaml'):
    if len(p) >= 3 and len(p[0]) == 1: tc[p[0]].add(p[2])
tby = collections.defaultdict(set)
for p in body('tigress_ci.dict.yaml'):
    if len(p) >= 3 and p[0] in wrank: tby[p[2]].add(p[0])
grid, hit, top = collections.Counter(), collections.defaultdict(set), []
for ch, cs in tc.items():
    if ch not in crank: continue
    full = max(cs, key=len)
    if any(len(c) < len(full) for c in cs): continue
    for w in tby.get(full, ()):
        cb, wb = cband(crank[ch]), wband(wrank[w])
        grid[(cb, wb)] += 1; hit[(cb, wb)].add(ch)
        if cb == CB[0] and wrank[w] <= 30000: top.append((ch, full, w, wrank[w]))
show('虎码秃版', grid, hit)
print('前1500 × 前3万：', sorted(top, key=lambda x: x[3]))
