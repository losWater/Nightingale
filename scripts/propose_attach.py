# -*- coding: utf-8 -*-
"""形似挂靠提案：蓝本 = jd1 官方 grouping（两端在册）+ 贪心新增变体的自然归宿。
每对算真实代价，≤1.0 的按代价升序应用，输出终态成绩与提案表。"""
import io
import sys
from pathlib import Path

import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))
from score import load_phonetic_keys, load_entries
from greedy import load_charset
from attach_fast import State

phon = load_phonetic_keys(BASE / "work/seed.yaml")
charset = load_charset()
entries = load_entries(BASE / "work/v174_assembled.tsv", phon, charset)
roots = set(l.strip() for l in open(BASE / "work/seed_roots.txt", encoding="utf-8") if l.strip())
st = State(entries)
J0, z0, w0 = st.J()

cfg = yaml.safe_load(open(BASE / "data/jdhe/简单鹤初稿20240512.yaml", encoding="utf-8"))
jd1g = {str(k): str(v) for k, v in (cfg["form"].get("grouping") or {}).items()}
proposals = []
for att, host in jd1g.items():
    if att in roots and host in roots and att not in "123456":
        proposals.append((att, host, "jd1官方"))
extra = [
    ("", "足", "足旁→足"), ("", "车", "车旁→车"), ("", "月", "青字底→月"),
    ("\U000201A2", "人", "人字头→人"), ("刂", "刀", "立刀→刀"), ("阝", "卩", "双耳→卩"),
    ("㇏", "4", "捺→点"), ("㇒", "3", "平撇→撇"), ("㇈", "5", "横折钩→折"),
    ("言", "讠", "言→讠"), ("死", "夕", "死→夕"), ("⺋", "巴", "⺋→巴"), ("⺌", "小", "小字头→小"),
]
seen = {(a, h) for a, h, _ in proposals}
for att, host, note in extra:
    if att in roots and host in roots and (att, host) not in seen:
        proposals.append((att, host, note))

print(f"基线 J={J0:.2f}; 形似提案 {len(proposals)} 对\n代价明细（升序）：")
rows = sorted((st.merge_cost(a, h), a, h, n) for a, h, n in proposals)
for c, a, h, n in rows:
    flag = "" if c <= 1.0 else "  ⚠️超标建议保持独立"
    print(f"  {a}→{h}: +{c:.2f}  ({n}){flag}")

applied = []
attached_set = set()
for c, a, h, n in rows:
    if a in attached_set or h in attached_set:
        continue
    real = st.merge_cost(a, h)
    if real <= 1.0:
        st.merge(a, h)
        applied.append((a, h, real))
        attached_set.add(a)
Jf, zf, wf = st.J()
mains = len(roots) - len(applied)
print(f"\n应用 {len(applied)} 对 → 主根 {mains} + 附属 {len(applied)}")
print(f"终态: J={Jf:.2f} 零阶{zf} 加权{wf:.2f}bp   (基线174根 J={J0:.2f}; 1.0 J≈81.3/零阶100/5.0bp)")
with open(BASE / "work/attach_proposal.tsv", "w", encoding="utf-8") as f:
    f.write("附属根\tcodepoint\t宿主\t代价\t依据\t是否采纳\n")
    adopted = {a for a, h, c in applied}
    for c, a, h, n in rows:
        cp = " ".join(f"U+{ord(x):04X}" for x in a)
        f.write(f"{a}\t{cp}\t{h}\t{c:.3f}\t{n}\t{'✓' if a in adopted else ''}\n")
