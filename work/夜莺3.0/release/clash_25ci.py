"""普通单字表 × 夜莺 2.5 字词表：字词冲突二维表（字档 × 词档）。
冲突：必须打全码的读音（无一二三简），其全码 = 2.5 字词表里某个多字词条的码。
字档按读音字频（夜桜字音基准分档），词档按虎码词库词频序（全部词条按权重排序；不在词库里的单列）。
用法：python release/clash_25ci.py <普通单字表> [输出csv]
"""
import collections, csv, json, sys
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib'))
from shuangpin import encode
L = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
E = yaml.load(open(ROOT / 'build/out/n30/elements.yaml', encoding='utf-8'), Loader=L)
META = json.load(open(ROOT / 'build/out/n30/meta.json', encoding='utf-8'))
N = sum(1 for e in E if e['拼音'] != 'reserved')
ONE = {(c, p) for c, p, n in json.load(open(ROOT / 'data/inputs/一二简.json', encoding='utf-8'))['fixed'] if n == 1}
CI25 = Path.home() / 'Nightingale/夜莺2.5/主表/字词表.txt'
table = sys.argv[1]

codes = collections.defaultdict(list)
for l in open(table, encoding='utf-8-sig'):
    p = l.rstrip('\n').split('\t')
    if len(p) >= 2 and len(p[0]) == 1:
        codes[p[0]].append(p[1])


def typed_full(i):
    """必须打全码时返回全码，否则 None。"""
    ch, py = E[i]['词'], E[i]['拼音']
    sy = encode(py, 'xiaohe')
    if (ch, py) in ONE and any(len(c) == 1 for c in codes[ch]):
        return None
    mine = [c for c in codes[ch] if c[:2] == sy]
    if any(len(c) < 4 for c in mine):
        return None
    full = [c for c in mine if len(c) == 4]
    return full[0] if full else None


# 词频序：虎码词库全部词条按权重
wt = {}
for l in open(ROOT / 'data/inputs/tigress_ci.dict.yaml', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) >= 2 and not l.startswith('#') and p[1].isdigit() and len(p[0]) > 1:
        wt[p[0]] = max(wt.get(p[0], 0), int(p[1]))
wrank = {w: r for r, w in enumerate(sorted(wt, key=lambda w: -wt[w]), 1)}

by_code = collections.defaultdict(list)
for l in open(CI25, encoding='utf-8-sig'):
    p = l.rstrip('\n').split('\t')
    if len(p) >= 2 and len(p[0]) > 1 and len(p[1]) == 4:
        by_code[p[1]].append(p[0])

order = sorted(range(N), key=lambda i: -E[i]['频率'])
crank = {i: r for r, i in enumerate(order, 1)}
tiers = [(name, set(META['tier_indices'][key])) for name, key in (('前1500', '1500'), ('前3500', '3500'), ('前6000', '6000'))]
CB = [t[0] for t in tiers] + ['6000后']
WB = ['前1万', '前3万', '前6万', '前13万', '不在词库']


def cband(i):
    return next((n for n, s in tiers if i in s), '6000后')


def wband(w):
    r = wrank.get(w)
    return '不在词库' if r is None else '前1万' if r <= 10000 else '前3万' if r <= 30000 else '前6万' if r <= 60000 else '前13万'


grid = collections.Counter(); chars = collections.defaultdict(set); rows = []
for i in range(N):
    f = typed_full(i)
    if not f or f not in by_code:
        continue
    for w in by_code[f]:
        cb, wb = cband(i), wband(w)
        grid[(cb, wb)] += 1; chars[(cb, wb)].add(i)
        rows.append([E[i]['词'], E[i]['拼音'], crank[i], cb, f, w, wrank.get(w, ''), wb])

print('冲突条数（字音×词）'); print('\t'.join(['字档\\词档'] + WB + ['合计']))
for cb in CB:
    print('\t'.join([cb] + [str(grid[(cb, wb)]) for wb in WB] + [str(sum(grid[(cb, wb)] for wb in WB))]))
print('\t'.join(['合计'] + [str(sum(grid[(cb, wb)] for cb in CB)) for wb in WB] + [str(sum(grid.values()))]))
print('\n涉及字音数'); print('\t'.join(['字档\\词档'] + WB))
for cb in CB:
    print('\t'.join([cb] + [str(len(chars[(cb, wb)])) for wb in WB]))
rows.sort(key=lambda x: (x[2], x[6] if x[6] != '' else 10 ** 9))
if len(sys.argv) > 2:
    with open(sys.argv[2], 'w', encoding='utf-8-sig', newline='') as fo:
        w = csv.writer(fo); w.writerow(['字', '拼音', '字频序', '字档', '全码', '2.5词', '词频序', '词档']); w.writerows(rows)
print('\n严重（前1500字 × 前3万词）：')
for r in rows:
    if r[3] == '前1500' and r[7] in ('前1万', '前3万'):
        print(r)
