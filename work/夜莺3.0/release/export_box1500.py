"""按形码盒子字频（笪骏）取前 1500 字，逐字列出简码与全码（码圈惯例：按字不按读音）。
用法：python release/export_box1500.py <普通单字表> <名字>"""
import sys, csv, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
SEL = " ;'456789"
table, name = sys.argv[1], sys.argv[2]
box = [l.rstrip('\n').split('\t') for l in open(ROOT / 'eval/box/默认字频.txt', encoding='utf-8') if '\t' in l]
codes = collections.defaultdict(list); pos = collections.Counter(); members = collections.defaultdict(list)
for l in open(table, encoding='utf-8-sig'):
    p = l.rstrip('\n').split('\t')
    if len(p) < 2 or len(p[0]) != 1:
        continue
    codes[p[0]].append((p[1], pos[p[1]])); members[p[1]].append(p[0]); pos[p[1]] += 1
tot = sum(float(f) for _, f in box)
rows, cnt = [], collections.Counter()
for k, (ch, f) in enumerate(box[:1500], 1):
    cs = codes.get(ch, [])
    shorts = sorted((c for c, _ in cs if len(c) < 4), key=len)
    fulls = [(c, i) for c, i in cs if len(c) == 4]
    kind = {1: '一简', 2: '二简', 3: '三简'}.get(len(shorts[0])) if shorts else '全码'
    cnt[kind] += 1
    full_txt = '、'.join(c + (SEL[min(i, 8)] if i else '') for c, i in fulls)
    note = [f'全码{c}第{i + 1}选' for c, i in fulls if i]
    same = sorted({m for c, _ in fulls for m in members[c] if m != ch})
    rows.append([k, ch, f'{1e6 * float(f) / tot:.1f}', shorts[0] if shorts else '', kind if shorts else '全码',
                 '、'.join(shorts[1:]), full_txt, '、'.join(same), '；'.join(note) or ('' if cs else '无编码')])
with open(Path.home() / f'Downloads/{name}_前1500字码表_盒子字频.csv', 'w', encoding='utf-8-sig', newline='') as fo:
    w = csv.writer(fo)
    w.writerow(['序', '字', '盒子字频(每百万)', '简码', '码长类型', '其他简码', '全码', '同全码的其他字', '备注'])
    w.writerows(rows)
print(name, dict(cnt), '纯全码字要选重', sum(1 for r in rows if r[4] == '全码' and r[8]))
