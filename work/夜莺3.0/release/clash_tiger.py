"""虎码秃版：单字 × 自家词库的字词冲突二维表（字档 × 词档），口径同 clash_25ci.py。
冲突：必须打全码的字（没有更短的码），其全码 = 词库里某个词的码（tigress_ci + tigress_simp_ci）。
字档按夜桜字音基准的字频（同字各读音相加；基准外的字记“通规外”），词档按虎码词库词频序。
用法：python release/clash_tiger.py [虎码目录] [输出csv]
"""
import collections, csv, sys
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parent.parent
L = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
D = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / 'Downloads/虎码秃版 鼠须管 （Mac）')


def body(f):
    on = False
    for l in open(D / f, encoding='utf-8'):
        if l.startswith('...'):
            on = True; continue
        if on and '\t' in l and not l.startswith('#'):
            yield l.rstrip('\n').split('\t')


E = yaml.load(open(ROOT / 'build/out/n30/elements.yaml', encoding='utf-8'), Loader=L)
cf = collections.Counter()
for e in E:
    if e['拼音'] != 'reserved' and len(e['词']) == 1:
        cf[e['词']] += e['频率']
crank = {c: r for r, (c, _) in enumerate(cf.most_common(), 1)}

codes = collections.defaultdict(set)
for p in body('tigress.dict.yaml'):
    if len(p) >= 3 and len(p[0]) == 1:
        codes[p[0]].add(p[2])

wt, by_code = {}, collections.defaultdict(set)
for f in ('tigress_ci.dict.yaml', 'tigress_simp_ci.dict.yaml'):
    for p in body(f):
        if len(p) >= 3 and len(p[0]) > 1 and p[1].isdigit():
            wt[p[0]] = max(wt.get(p[0], 0), int(p[1])); by_code[p[2]].add(p[0])
wrank = {w: r for r, w in enumerate(sorted(wt, key=lambda w: -wt[w]), 1)}

CB = ['前1500', '1500–3500', '3500–6000', '6000后', '通规外']
WB = ['前1万', '1–3万', '3–6万', '6万后']
cband = lambda r: CB[0] if r <= 1500 else CB[1] if r <= 3500 else CB[2] if r <= 6000 else CB[3] if r < 10 ** 6 else CB[4]
wband = lambda r: WB[0] if r <= 10000 else WB[1] if r <= 30000 else WB[2] if r <= 60000 else WB[3]

grid = collections.Counter(); hit = collections.defaultdict(set); rows = []
full_only = 0
for ch, cs in codes.items():
    full = max(cs, key=len)
    if any(len(c) < len(full) for c in cs):
        continue                                   # 有简码：全码位让位
    full_only += 1
    for w in by_code.get(full, ()):
        r = crank.get(ch, 10 ** 6); cb, wb = cband(r), wband(wrank[w])
        grid[(cb, wb)] += 1; hit[(cb, wb)].add(ch)
        rows.append([ch, r if r < 10 ** 6 else '', cb, full, w, wrank[w], wb])

print('虎码单字', len(codes), '其中只能打全码的', full_only)
print('冲突条数（字×词）'); print('\t'.join(['字档\\词档'] + WB + ['合计']))
for cb in CB:
    print('\t'.join([cb] + [str(grid[(cb, wb)]) for wb in WB] + [str(sum(grid[(cb, wb)] for wb in WB))]))
print('\t'.join(['合计'] + [str(sum(grid[(cb, wb)] for cb in CB)) for wb in WB] + [str(sum(grid.values()))]))
print('\n涉及字数'); print('\t'.join(['字档\\词档'] + WB))
for cb in CB:
    print('\t'.join([cb] + [str(len(hit[(cb, wb)])) for wb in WB]))
rows.sort(key=lambda x: (x[1] if x[1] != '' else 10 ** 9, x[5]))
print('\n前1500字的冲突：')
for r in rows:
    if r[2] == '前1500': print(r)
if len(sys.argv) > 2:
    with open(sys.argv[2], 'w', encoding='utf-8-sig', newline='') as fo:
        w = csv.writer(fo); w.writerow(['字', '字频序', '字档', '全码', '撞的词', '词频序', '词档']); w.writerows(rows)
