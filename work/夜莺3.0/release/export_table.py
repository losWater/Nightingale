"""从普通单字表（字\\t码）导出：前1500字码表、全部字词冲突明细。读音、字频、分档用夜桜字音基准（与 3.0 同口径）。
用法：python release/export_table.py <普通单字表> <名字>"""
import json, sys, csv, collections
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'eval')); sys.path.insert(0, str(ROOT / 'lib'))
from word_clash import top_words
from shuangpin import encode
L = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
E = yaml.load(open(ROOT / 'build/out/n30/elements.yaml', encoding='utf-8'), Loader=L)
META = json.load(open(ROOT / 'build/out/n30/meta.json', encoding='utf-8'))
N = sum(1 for e in E if e['拼音'] != 'reserved')
ONE = {(c, p) for c, p, n in json.load(open(ROOT / 'data/inputs/2.5一二简固定.json', encoding='utf-8'))['fixed'] if n == 1}
SEL = " ;'456789"
table, name = sys.argv[1], sys.argv[2]

codes = collections.defaultdict(list)          # 字 -> [(码, 该码下的序位)]
pos = collections.Counter(); members = collections.defaultdict(list)
for l in open(table, encoding='utf-8-sig'):
    p = l.rstrip('\n').split('\t')
    if len(p) < 2 or len(p[0]) != 1:
        continue
    ch, code = p[0], p[1]
    codes[ch].append((code, pos[code])); members[code].append(ch); pos[code] += 1


def reading(i):
    ch, py = E[i]['词'], E[i]['拼音']
    sy = encode(py, 'xiaohe')
    short = full = None
    for code, k in codes[ch]:
        if len(code) == 1:
            if (ch, py) in ONE: short = short or code
        elif code[:2] == sy:
            if len(code) < 4 and (short is None or len(code) < len(short)): short = code
            if len(code) == 4 and (full is None or k < full[1]): full = (code, k)
    return short, full


R = [reading(i) for i in range(N)]
T1500 = sorted(META['tier_indices']['1500'], key=lambda i: -E[i]['频率']); S1500 = set(T1500)
S3500 = set(META['tier_indices']['3500'])
rank = {i: r for r, i in enumerate(sorted(range(N), key=lambda i: -E[i]['频率']), 1)}
tot = sum(e['频率'] for e in E[:N])
readings = collections.Counter(E[i]['词'] for i in range(N))
DL = Path.home() / 'Downloads'

rows = []
for k, i in enumerate(T1500, 1):
    ch = E[i]['词']; short, full = R[i]
    kind = {1: '一简', 2: '二简', 3: '三简'}.get(len(short)) if short else ''
    fc, fr = full if full else ('', 0)
    note = (['多音'] if readings[ch] > 1 else []) + ([f'全码第{fr + 1}选'] if fr else []) + ([] if full else ['无全码'])
    rows.append([k, ch, E[i]['拼音'], f"{1e6 * E[i]['频率'] / tot:.1f}", short or '', kind, fc + (SEL[fr] if fr else ''),
                 '、'.join(c for c in members.get(fc, []) if c != ch), '；'.join(note)])
with open(DL / f'{name}_前1500字码表.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f); w.writerow(['序', '字', '拼音', '字频(每百万)', '简码', '简码类型', '全码', '同全码的其他字', '备注']); w.writerows(rows)
print('码表', len(rows), dict(collections.Counter(r[5] or '全码' for r in rows)),
      '全码要选重的纯全码字', sum(1 for r in rows if not r[5] and '选' in r[8]))

words = top_words('xiaohe', 200000)
by_code = collections.defaultdict(list)
for r, (wd, code) in enumerate(words, 1):
    by_code[code].append((r, wd))
out, cnt = [], collections.Counter()
for i in range(N):
    short, full = R[i]
    if short or not full or full[0] not in by_code:
        continue
    band = '前1500字' if i in S1500 else ('前3500字' if i in S3500 else '3500字以后')
    for r, wd in by_code[full[0]]:
        cat = ('①' if i in S1500 and r <= 10000 else '') + ('②' if i in S1500 and r <= 30000 else '') + ('③' if i in S3500 and r <= 10000 else '')
        wband = '前1万词' if r <= 10000 else '前3万词' if r <= 30000 else '前5万词' if r <= 50000 else '5万词以后'
        cnt[(band, wband)] += 1
        out.append([E[i]['词'], E[i]['拼音'], rank[i], band, full[0], wd, r, wband, cat])
out.sort(key=lambda x: (x[2], x[6]))
with open(DL / f'{name}_字词冲突全表.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f); w.writerow(['字', '拼音', '字频序', '字档', '全码', '撞的词', '词频序', '词档', '计入指标']); w.writerows(out)
print('冲突条数', len(out))
for b in ('前1500字', '前3500字', '3500字以后'):
    print(b, [cnt[(b, wb)] for wb in ('前1万词', '前3万词', '前5万词', '5万词以后')])
print('①②③', [sum(c in x[8] for x in out) for c in '①②③'])
for x in out:
    if x[8]: print(x)
