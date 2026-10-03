"""普通单字表门禁检查（实际选重口径）：前1521/3571 选重、字词撞①②③、前1500四码。
用法：.venv/bin/python release/check_table.py <普通单字表> [有一简:1/0]
"""
import collections, json, sys, yaml
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib')); sys.path.insert(0, str(ROOT / 'eval'))
from shuangpin import encode
from word_clash import top_words
E = yaml.load(open(ROOT / 'build/out/n30/elements.yaml', encoding='utf-8'), Loader=yaml.CSafeLoader)
META = json.load(open(ROOT / 'build/out/n30/meta.json', encoding='utf-8'))
N = sum(1 for e in E if e['拼音'] != 'reserved')
g_of = {r: g for g, rs in META['groups'].items() for r in rs}
sp = json.load(open(ROOT / 'data/baseline/splits.json', encoding='utf-8'))
T1, T3 = set(META['tier_indices']['1500']), set(META['tier_indices']['3500'])
ONE = {(c, p) for c, p, n in json.load(open(ROOT / 'data/inputs/3.0一二简.json', encoding='utf-8'))['fixed'] if n == 1}
path = sys.argv[1]; use_one = (sys.argv[2] if len(sys.argv) > 2 else '1') == '1'
wr = {}
for r, (w, c) in enumerate(top_words('xiaohe', 30000), 1): wr.setdefault(c, []).append((r, w))
pos, codes, k = {}, collections.defaultdict(list), collections.Counter()
for l in open(path, encoding='utf-8-sig'):
    p = l.rstrip('\n').split('\t')
    if len(p) < 2 or len(p[0]) != 1: continue
    pos[(p[0], p[1])] = k[p[1]]; k[p[1]] += 1; codes[p[0]].append(p[1])
typed, four = [], 0
for i in range(N):
    ch, py = E[i]['词'], E[i]['拼音']; sy = encode(py, 'xiaohe')
    if use_one and (ch, py) in ONE: continue
    mine = [c for c in codes[ch] if c[:2] == sy]
    if any(len(c) < 4 for c in mine): continue
    if i in T1: four += 1
    full = min((c for c in mine if len(c) == 4), key=lambda c: pos[(ch, c)], default=None)
    if full: typed.append((pos[(ch, full)], i, full))
by = collections.defaultdict(list)
for p, i, f in typed: by[f].append((p, i))
d1, d3 = [], []
for f, lst in by.items():
    seen = []
    for p, i in sorted(lst):
        sig = (g_of[sp[E[i]['词']][0][0]], g_of[sp[E[i]['词']][-1][0]])
        other = next((j for j, s in seen if s != sig), None)
        if other is not None:
            if i in T1: d1.append((E[i]['词'], E[other]['词'], f))
            if i in T3: d3.append((E[i]['词'], E[other]['词'], f))
        seen.append((i, sig))
c1 = [(E[i]['词'], f) for p, i, f in typed if i in T1 and f in wr and wr[f][0][0] <= 10000]
c2 = [(E[i]['词'], f) for p, i, f in typed if i in T1 and f in wr]
c3 = [(E[i]['词'], f) for p, i, f in typed if i in T3 and f in wr and wr[f][0][0] <= 10000]
print(f'前1521选重 {len(d1)} {d1}  前3571选重 {len(d3)} {d3}')
print(f'字词撞① {len(c1)} {c1}  ② {len(c2)}  ③ {len(c3)} {c3}')
print(f'前1500四码 {four}')
