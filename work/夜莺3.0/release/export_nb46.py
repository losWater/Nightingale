"""导出 NB46：前1500字（1521 个读音）码表、全部字词冲突明细。"""
import json, sys, csv, collections, glob
from pathlib import Path
import yaml
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'eval'))
from word_clash import top_words
L = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
E = yaml.load(open(ROOT / 'build/out/n30/elements.yaml', encoding='utf-8'), Loader=L)
META = json.load(open(ROOT / 'build/out/n30/meta.json', encoding='utf-8'))
N = sum(1 for e in E if e['拼音'] != 'reserved')
C = [l.rstrip('\n').split('\t') for l in open(glob.glob(str(ROOT / 'runs/n30_nb/nb46/output-*/code.txt'))[0], encoding='utf-8')][:N]
SEL = " ;'456789"
T1500 = set(META['tier_indices']['1500']); T3500 = set(META['tier_indices']['3500'])
DL = Path.home() / 'Downloads'
tot = sum(e['频率'] for e in E[:N])
rank_char = {}
for i in sorted(range(N), key=lambda i: -E[i]['频率']):
    rank_char.setdefault(i, len(rank_char) + 1)
readings = collections.Counter(E[i]['词'] for i in range(N))
by_full = collections.defaultdict(list)
for i in range(N):
    by_full[C[i][1]].append(i)

# 1. 前1500字码表
rows = []
for k, i in enumerate(sorted(T1500, key=lambda i: -E[i]['频率']), 1):
    ch, full, fr, short, sr = C[i][0], C[i][1], int(C[i][2]), C[i][3], int(C[i][4])
    kind = {1: '一简', 2: '二简', 3: '三简'}.get(len(short), '') if len(short) < 4 else ''
    same = [C[j][0] for j in by_full[full] if j != i]
    note = []
    if readings[ch] > 1: note.append('多音')
    if fr: note.append(f'全码第{fr + 1}选')
    rows.append([k, ch, E[i]['拼音'], f"{1e6 * E[i]['频率'] / tot:.1f}", short if kind else '', kind, full + (SEL[fr] if fr else ''),
                 '、'.join(same), '；'.join(note)])
with open(DL / '夜莺3.0_NB46_前1500字码表.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f); w.writerow(['序', '字', '拼音', '字频(每百万)', '简码', '简码类型', '全码', '同全码的其他字', '备注']); w.writerows(rows)
print('码表', len(rows), collections.Counter(r[5] or '全码' for r in rows))

# 2. 字词冲突：凡“必须打全码”的读音（无一二三简），其全码等于某二字词的码
words = top_words('xiaohe', 200000)
by_code = collections.defaultdict(list)
for r, (wd, code) in enumerate(words, 1):
    by_code[code].append((r, wd))
out, cnt = [], collections.Counter()
for i in range(N):
    full, short = C[i][1], C[i][3]
    if len(short) < 4 or full not in by_code:
        continue
    for r, wd in by_code[full]:
        cr = sorted(T1500, key=lambda j: -E[j]['频率']).index(i) + 1 if i in T1500 else None
        cat = []
        if i in T1500 and r <= 10000: cat.append('①')
        if i in T1500 and r <= 30000: cat.append('②')
        if i in T3500 and r <= 10000: cat.append('③')
        band = '前1500字' if i in T1500 else ('前3500字' if i in T3500 else '3500字以后')
        wband = '前1万词' if r <= 10000 else '前3万词' if r <= 30000 else '前5万词' if r <= 50000 else '5万词以后'
        cnt[(band, wband)] += 1
        out.append([C[i][0], E[i]['拼音'], rank_char[i], band, full, wd, r, wband, ''.join(cat)])
out.sort(key=lambda x: (x[2], x[6]))
with open(DL / '夜莺3.0_NB46_字词冲突全表.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f); w.writerow(['字', '拼音', '字频序', '字档', '全码', '撞的词', '词频序', '词档', '计入指标']); w.writerows(out)
print('词总数', len(words), '冲突条数', len(out))
for b in ('前1500字', '前3500字', '3500字以后'):
    print(b, {wb: cnt[(b, wb)] for wb in ('前1万词', '前3万词', '前5万词', '5万词以后')})
print('① ② ③ =', sum('①' in x[8] for x in out), sum('②' in x[8] for x in out), sum('③' in x[8] for x in out))
for x in out:
    if x[8] or x[6] <= 30000: print(x)
