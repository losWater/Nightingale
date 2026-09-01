# -*- coding: utf-8 -*-
"""夜莺码纯单字简码表生成：一/二/三简各二重，出简不出全，四码免选。

输入: work/nightingale_v01_code.txt (chai 输出，字\t全码\t序\t简码\t序)
      频率取 elements.yaml 同源的 v176_assembled.tsv
输出: work/夜莺码v0.1纯单版.txt (字\t码，按码升序，同码内按频率降序)
"""
import io
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
WORK = BASE / "work"

# 字→全码、字→频率
full = {}
freq = {}
for line in open(WORK / "nightingale_v01_code.txt", encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) >= 2 and len(p[0]) == 1 and p[0] not in full:
        full[p[0]] = p[1]
for line in open(WORK / "v176_assembled.tsv", encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) >= 3 and len(p[0]) == 1:
        freq[p[0]] = max(freq.get(p[0], 0), int(p[2]))

chars = sorted(full, key=lambda c: -freq.get(c, 0))
assigned = {}
MAX_PER = 2  # 二重

for L in (1, 2, 3):
    bucket = defaultdict(list)
    for c in chars:
        if c in assigned:
            continue
        bucket[full[c][:L]].append(c)
    for prefix, cands in bucket.items():
        for c in cands[:MAX_PER]:
            assigned[c] = prefix

rows = []
for c in chars:
    rows.append((assigned.get(c, full[c]), -freq.get(c, 0), c))
rows.sort()
with open(WORK / "夜莺码v0.1纯单版.txt", "w", encoding="utf-8", newline="\n") as f:
    for code, negf, c in rows:
        f.write(f"{c}\t{code}\n")

# 统计
from collections import Counter
lv = Counter(len(assigned[c]) for c in assigned)
total_f = sum(freq.get(c, 0) for c in chars) or 1
wkl = sum((len(assigned.get(c, full[c])) + 1) * freq.get(c, 0) for c in chars) / total_f
# 选重（同码非首位）
by_code = defaultdict(list)
for code, negf, c in rows:
    by_code[code].append(c)
dup = sum(len(v) - 1 for v in by_code.values() if len(v) > 1)
dup_w = sum(freq.get(c, 0) for v in by_code.values() for c in v[1:]) / total_f
print(f"简码分配: 一简 {lv[1]} 字, 二简 {lv[2]} 字, 三简 {lv[3]} 字, 全码 {len(chars)-len(assigned)} 字")
print(f"估算加权键长(含上屏): {wkl:.3f}")
print(f"码表内选重 {dup} 条, 频率加权 {dup_w*100:.3f}%（含刻意的二重简码）")
