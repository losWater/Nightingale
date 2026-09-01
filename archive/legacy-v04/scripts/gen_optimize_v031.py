# -*- coding: utf-8 -*-
"""v0.3.1 精修退火输入：最终拆分（51 挂靠）+ 真低温局部优化。
elements = v03_assembled(全部挂靠已生效) + 5万高频词
mapping/space = v0.3 布局热启动 + 51 挂靠 Grouped
t 0.05→1e-4, 100 万步（目标：赎回字字撞车，不翻布局大盘）
"""
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "work/optimize"
TOP_WORDS = 50000

char_items = []
main_phon = {}
best_f = {}
for line in open(BASE / "work/v03_assembled.tsv", encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) < 3 or len(p[0]) != 1:
        continue
    elems = [json.loads(t) for t in p[1].split(" ")]
    seq = [{"element": e["element"], "index": e.get("index", 0)} for e in elems]
    f = int(p[2])
    char_items.append({"词": p[0], "元素序列": seq, "频率": f})
    phon = [e["element"] for e in elems if e["element"].startswith(("szm-", "mzm-"))]
    if len(phon) == 2 and f >= best_f.get(p[0], -1):
        best_f[p[0]] = f
        main_phon[p[0]] = tuple(phon)

wfreq = {}
for line in open(BASE / "repos/webchai/packages/hanzi-chai/src/data/dictionary.txt", encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) >= 3 and len(p[0]) >= 2:
        try:
            wfreq[p[0]] = max(wfreq.get(p[0], 0), int(p[2]))
        except ValueError:
            pass
cands = []
for line in open(BASE / "大词库.txt", encoding="utf-8-sig"):
    w = line.strip()
    if len(w) >= 2 and all(c in main_phon for c in w):
        f = wfreq.get(w, 0)
        if f > 0:
            cands.append((f, w))
cands.sort(reverse=True)
word_items = []
for f, w in cands[:TOP_WORDS]:
    ph = [main_phon[c] for c in w]
    if len(w) == 2:
        els = [ph[0][0], ph[0][1], ph[1][0], ph[1][1]]
    elif len(w) == 3:
        els = [ph[0][0], ph[1][0], ph[2][0], ph[2][1]]
    else:
        els = [ph[0][0], ph[1][0], ph[2][0], ph[3][0]]
    word_items.append({"词": w, "元素序列": [{"element": e, "index": 0} for e in els], "频率": f})
items = char_items + word_items
yaml.safe_dump(items, open(OUT / "elements_v031.yaml", "w", encoding="utf-8"),
               allow_unicode=True, sort_keys=False, width=10000)
print(f"elements_v031: 单字 {len(char_items)} + 词 {len(word_items)}")

cfg = yaml.safe_load(open(OUT / "config_v03.yaml", encoding="utf-8"))
layout = yaml.safe_load(open(BASE / "releases/v0.3/夜莺码v0.3键位布局.yaml", encoding="utf-8"))
mapping = {str(k): v for k, v in layout["form"]["mapping"].items()}
cfg["form"]["mapping"] = mapping
space = dict(cfg["form"]["mapping_space"])
for k, v in mapping.items():
    if isinstance(v, dict):
        space[k] = [{"value": {"element": str(v["element"])}, "score": 0.0}]
cfg["form"]["mapping_space"] = space
cfg["optimization"]["metaheuristic"] = {
    "algorithm": "SimulatedAnnealing",
    "parameters": {"t_max": 0.05, "t_min": 1e-4, "steps": 1000000},
}
cfg["info"]["version"] = "0.3.1-refine"
yaml.safe_dump(cfg, open(OUT / "config_v031.yaml", "w", encoding="utf-8"),
               allow_unicode=True, sort_keys=False, width=10000)
print("config_v031 就绪（t 0.05→1e-4, 100万步, 51挂靠随行）")
