# -*- coding: utf-8 -*-
"""键位层对账：重算元素序列 → 按初稿 mapping 转四码，对比官方纯单版码表。"""
import json
import re
import yaml
import io, sys
from collections import Counter
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent

cfg = yaml.safe_load(open(BASE / "data/jdhe/简单鹤初稿20240512.yaml", encoding="utf-8"))
mapping = {str(k): v for k, v in cfg["form"]["mapping"].items()}
group = {str(k): str(v) for k, v in (cfg["form"].get("grouping") or {}).items()}

def key_of(name: str):
    seen = set()
    while name in group and name not in seen:
        seen.add(name)
        name = group[name]
    v = mapping.get(name)
    return v if isinstance(v, str) else None

official = {}
for line in open(BASE / "data/jdhe/简单鹤V1.0纯单版.txt", encoding="utf-8-sig"):
    p = line.rstrip("\n").split("\t")
    if len(p) >= 2 and len(p[0]) == 1 and re.fullmatch(r"[a-z]{4}", p[1]) and p[0] not in official:
        official[p[0]] = p[1]

ours = {}
skipped = Counter()
for line in open(BASE / "work/jd1_assembled.tsv", encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) < 3 or len(p[0]) != 1:
        continue
    ch = p[0]
    if ch in ours:
        continue
    keys = []
    bad = None
    for tok in p[1].split(" "):
        try:
            e = json.loads(tok)
        except json.JSONDecodeError:
            continue
        name = e["element"] if isinstance(e, dict) else str(e)
        k = key_of(name)
        if k:
            keys.append(k)
        else:
            bad = name
    if bad:
        skipped[bad] += 1
    elif len(keys) == 4:
        ours[ch] = "".join(keys)
    else:
        skipped[f"len={len(keys)}"] += 1

common = set(official) & set(ours)
n = len(common)
full = sum(1 for c in common if official[c] == ours[c])
print(f"对比 {n} 字（官方四码 {len(official)}，重算成码 {len(ours)}）")
print(f"四码全同: {full} ({full/n*100:.2f}%)")
for i, lab in enumerate(["声", "韵", "首根", "末根"]):
    m = sum(1 for c in common if official[c][i] == ours[c][i])
    print(f"  第{i+1}码({lab})同: {m} ({m/n*100:.2f}%)")
if skipped:
    print("跳过原因 top5:", skipped.most_common(5))

diffs = [(c, official[c], ours[c]) for c in common if official[c] != ours[c]]
cnt = Counter()
for c, o, u in diffs:
    cnt["".join("1234"[i] for i in range(4) if o[i] != u[i])] += 1
print("差异位分布:", dict(cnt.most_common(8)))
with open(BASE / "work/key_diffs.tsv", "w", encoding="utf-8") as f:
    f.write("字\t官方\t重算\n")
    for c, o, u in sorted(diffs):
        f.write(f"{c}\t{o}\t{u}\n")
print(f"明细: work/key_diffs.tsv ({len(diffs)} 字)")
