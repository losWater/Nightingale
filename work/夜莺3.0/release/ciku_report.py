"""3.0 字词表与 2.5 字词表的首选对比报告：逐码位比较首选，分类并给出频率。
用法：.venv/bin/python release/ciku_report.py [3.0字词表] [输出csv]
"""
import collections, csv, sys, yaml
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib'))
from shuangpin import encode

new = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'release/tables/夜莺3.0_NB46_字词表.txt'
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.home() / 'Downloads/夜莺3.0_字词表首选变化报告.csv'


def rd(p): return [tuple(l.rstrip('\n').split('\t')[:2]) for l in open(p, encoding='utf-8-sig') if '\t' in l]


ga, gb = collections.defaultdict(list), collections.defaultdict(list)
for t, c in rd(Path.home() / 'Nightingale/夜莺2.5/主表/字词表.txt'): ga[c].append(t)
for t, c in rd(new): gb[c].append(t)
E = yaml.load(open(ROOT / 'build/out/n30/elements.yaml', encoding='utf-8'), Loader=yaml.CSafeLoader)
tot = sum(e['频率'] for e in E if e['拼音'] != 'reserved')
rf = collections.Counter()
for e in E:
    if e['拼音'] == 'reserved': continue
    try: rf[(e['词'], encode(e['拼音'], 'xiaohe'))] += e['频率'] / tot * 1e6
    except Exception: pass
wt = {}
for l in open(ROOT / 'data/inputs/tigress_ci.dict.yaml', encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) >= 2 and not l.startswith('#') and p[1].isdigit() and len(p[0]) > 1: wt[p[0]] = max(wt.get(p[0], 0), int(p[1]))
wtot = sum(wt.values())


def fq(t, c):
    return rf.get((t, c[:2]), 0) if len(t) == 1 else (wt[t] / wtot * 1e6 if t in wt else 0)


KINDS = ['词被字顶掉·字是新搬来的', '词被字顶掉·字原本就在（不再让位）', '字让给词（字还在本码位）', '字搬走了，首选变成词', '字→字', '词→词']
cat = collections.defaultdict(list)
for c in set(ga) | set(gb):
    a, b = ga.get(c, []), gb.get(c, [])
    if not a or not b or a[0] == b[0]: continue
    x, y = a[0], b[0]
    if len(x) > 1 and len(y) == 1: k = KINDS[0] if y not in a else KINDS[1]
    elif len(x) == 1 and len(y) > 1: k = KINDS[2] if x in b else KINDS[3]
    elif len(x) == 1 and len(y) == 1: k = KINDS[4]
    else: k = KINDS[5]
    cat[k].append((c, x, y, fq(x, c), fq(y, c)))
with open(out, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f); w.writerow(['类型', '码', '码长', '2.5首选', '3.0首选', '2.5首选频率(每百万)', '3.0首选频率(每百万)'])
    for k in KINDS:
        for c, x, y, a, b in sorted(cat.get(k, []), key=lambda r: -r[3]):
            w.writerow([k, c, len(c), x, y, f'{a:.2f}', f'{b:.2f}'])
print(out)
for k in KINDS:
    v = cat.get(k, [])
    print(f'{k}: {len(v)}（短码位 {sum(1 for r in v if len(r[0]) < 4)}）')
for k in KINDS[:2]:
    print(f'\n{k}，按被顶掉的词的频率前 12：')
    for c, x, y, a, b in sorted(cat.get(k, []), key=lambda r: -r[3])[:12]: print(f'  {c}  {x}({a:.1f}) → {y}({b:.2f})')
