# -*- coding: utf-8 -*-
"""v0.3 字词混合退火输入生成。

- elements: 8千单字(全读音) + 高频词5万(元素序列=纯音码, 按构词公式)
- mapping: v0.2 最优布局热启动 + 士→土 挂靠
- objective: characters_full/short 保留 + words_full(挡词惩罚)
- 低温精修: t 0.17→1e-4, 2M步（保住现有键位大盘）
输出: work/optimize/config_v03.yaml, elements_v03.yaml
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

# --- 单字条目 + 每字主读音的音码元素 ---
char_items = []
main_phon = {}   # 字 -> (szm元素, mzm元素) 主读音
best_f = {}
for line in open(BASE / "work/v176_assembled.tsv", encoding="utf-8"):
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

# --- 词条目（元素序列=音码, 构词公式）---
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
yaml.safe_dump(items, open(OUT / "elements_v03.yaml", "w", encoding="utf-8"),
               allow_unicode=True, sort_keys=False, width=10000)
print(f"elements_v03: 单字 {len(char_items)} + 词 {len(word_items)}")

# --- 配置 ---
cfg = yaml.safe_load(open(OUT / "config.yaml", encoding="utf-8"))
best = yaml.safe_load(open(BASE / "work/nightingale_v01_layout.yaml", encoding="utf-8"))
mapping = dict(best["form"]["mapping"])
mapping["士"] = {"element": "土"}
cfg["form"]["mapping"] = mapping
space = dict(cfg["form"]["mapping_space"])
space["士"] = [{"value": {"element": "土"}, "score": 0.0}]
cfg["form"]["mapping_space"] = space
cfg["optimization"]["objective"]["words_full"] = {
    "tiers": [{"top": 2000, "duplication": 150}, {"top": 20000, "duplication": 40}],
    "duplication": 15,
    "levels": [],
}
cfg["optimization"]["metaheuristic"] = {
    "algorithm": "SimulatedAnnealing",
    "parameters": {"t_max": 0.17, "t_min": 1e-4, "steps": 2000000},
}
cfg["info"]["version"] = "0.3-mixed"
yaml.safe_dump(cfg, open(OUT / "config_v03.yaml", "w", encoding="utf-8"),
               allow_unicode=True, sort_keys=False, width=10000)
print("config_v03 就绪（低温精修 0.17→1e-4, 2M 步, 士→土 已挂）")
