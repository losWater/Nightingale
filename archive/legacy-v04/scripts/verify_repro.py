# -*- coding: utf-8 -*-
"""对账：headless 重算的 1.0 拆分 vs 考古解码的官方拆分表（首末根）。"""
import json
import re
import yaml
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
WORK = BASE / "work"
JDHE = BASE / "data" / "jdhe"

# 附属根→主根 映射（从原始 2.3 yaml 的 grouping 取）
cfg = yaml.safe_load(open(JDHE / "简单鹤初稿20240512.yaml", encoding="utf-8"))
group = {str(k): str(v) for k, v in (cfg["form"].get("grouping") or {}).items()}
STROKE = {"横": "1", "竖": "2", "撇": "3", "点": "4", "折": "5"}

def canon(c: str) -> str:
    c = STROKE.get(c, c)
    seen = set()
    while c in group and c not in seen:
        seen.add(c)
        c = group[c]
    return c

# 官方拆分表: 字\t〔首末根¦码〕
official = {}
pat = re.compile(r"^(.)\t〔(.+?)¦")
for line in open(JDHE / "拆分表_解码.txt", encoding="utf-8"):
    m = pat.match(line)
    if m:
        comps = m.group(2)
        official[m.group(1)] = (canon(comps[0]), canon(comps[-1]))

# 重算结果: 字\t{json} {json}...\t频率
ours = {}
for line in open(WORK / "jd1_assembled.tsv", encoding="utf-8"):
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 3 or len(parts[0]) != 1:
        continue
    ch = parts[0]
    roots = []
    for tok in parts[1].split(" "):
        try:
            e = json.loads(tok)
        except json.JSONDecodeError:
            continue
        name = e["element"] if isinstance(e, dict) else str(e)
        if isinstance(name, str) and not (name.startswith("szm-") or name.startswith("mzm-")):
            roots.append(name)
    if roots and ch not in ours:  # 多音字取第一条
        ours[ch] = (canon(roots[0]), canon(roots[-1]))

common = set(official) & set(ours)
match = sum(1 for c in common if official[c] == ours[c])
first_match = sum(1 for c in common if official[c][0] == ours[c][0])
last_match = sum(1 for c in common if official[c][1] == ours[c][1])
print(f"对比字数: {len(common)}（官方表 {len(official)}，重算 {len(ours)} 单字）")
print(f"首末根全同: {match} ({match/len(common)*100:.2f}%)")
print(f"首根同: {first_match} ({first_match/len(common)*100:.2f}%)  末根同: {last_match} ({last_match/len(common)*100:.2f}%)")

diffs = [(c, official[c], ours[c]) for c in common if official[c] != ours[c]]
# 差异模式统计
pat_counter = Counter()
for c, o, u in diffs:
    pat_counter[(o, u)] += 1
print("\n最常见差异模式 (官方→重算):")
for (o, u), n in pat_counter.most_common(15):
    print(f"  {o[0]}{o[1]} → {u[0]}{u[1]} : {n} 字")
with open(WORK / "repro_diffs.tsv", "w", encoding="utf-8") as f:
    f.write("字\t官方首\t官方末\t重算首\t重算末\n")
    for c, o, u in sorted(diffs):
        f.write(f"{c}\t{o[0]}\t{o[1]}\t{u[0]}\t{u[1]}\n")
print(f"\n差异明细: {WORK/'repro_diffs.tsv'} ({len(diffs)} 字)")
