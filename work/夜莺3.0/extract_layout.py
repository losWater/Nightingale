"""从夜莺2.5拆分原本（工具箱拆分查询的数据源）提取正式布局：字根→键、逐字拆分。只读夜莺仓库。"""
import json, re, sys, collections
from pathlib import Path

SRC = Path.home() / 'Nightingale/夜莺2.5/资料/拆分原本.html'
TABLE = Path.home() / 'Nightingale/夜莺2.5/主表/单字表.txt'
OUT = Path(__file__).parent / 'data/baseline'

s = SRC.read_text(encoding='utf-8-sig')
dec = json.JSONDecoder()
m = re.search(r'\b(?:const|let) views\s*=\s*', s)
views = dec.raw_decode(s[m.end():])[0]
q = views['query']
D = dec.raw_decode(q[re.search(r'\bconst D\s*=\s*', q).end():])[0]

root_key = {}
conflicts = collections.defaultdict(set)
for c, d in D.items():
    for r in d.get('根', []):
        root_key.setdefault(r['根'], r['键'])
        conflicts[r['根']].add(r['键'])
bad = {r: ks for r, ks in conflicts.items() if len(ks) > 1}

# 与单字表核对：四码正式码第3/4位应为首/末根键
codes = collections.defaultdict(set)
for l in TABLE.read_text(encoding='utf-8-sig').splitlines():
    p = l.split('\t')
    if len(p) >= 2 and len(p[0]) == 1:
        codes[p[0]].add(p[1])
ok = miss = 0
mism = []
for c, d in D.items():
    rs = d.get('根', [])
    if not rs or c not in codes:
        continue
    tail = rs[0]['键'] + rs[-1]['键']
    if any(len(k) == 4 and k[2:] == tail for k in codes[c]):
        ok += 1
    else:
        miss += 1
        if len(mism) < 15:
            mism.append((c, [r['根'] for r in rs], tail, sorted(codes[c])))

OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'root_key.json').write_text(json.dumps(root_key, ensure_ascii=False, indent=1), encoding='utf-8')
(OUT / 'splits.json').write_text(json.dumps({c: [(r['根'], r['键']) for r in d.get('根', [])] for c, d in D.items()}, ensure_ascii=False), encoding='utf-8')
print('keys of D sample:', list(next(iter(D.values())).keys()))
print('字数', len(D), '有拆分', sum(1 for d in D.values() if d.get('根')), '字根数', len(root_key), '一根多键', len(bad))
print('单字表核对：首末根键与某个四码后两位一致', ok, '不一致', miss)
for x in mism: print('  ', x)
per_key = collections.Counter(root_key.values())
print('每键字根数', ''.join(f'{k}{per_key[k]} ' for k in 'abcdefghijklmnopqrstuvwxyz'))
