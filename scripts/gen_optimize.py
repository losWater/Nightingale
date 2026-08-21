# -*- coding: utf-8 -*-
"""生成 chai.exe v0.4 退火输入：work/optimize/config.yaml + elements.yaml。

设计：
- alphabet 26 键（音码占用 p），select_keys [_, ;]
- 音码元素：mapping 钉死 + 决策空间单候选（不可动）
- 143 根 + 5 笔画根：决策空间 = 25 键（无 p）→ 四码字不以 p 结尾
- 附属形：mapping/空间均为 {element: 宿主}
- 热启动：同名根继承 1.0 键位（在 p 上的改随机非 p 键）
"""
import io
import json
import random
import sys
from pathlib import Path

import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
WORK = BASE / "work"
OUT = WORK / "optimize"
OUT.mkdir(exist_ok=True)
random.seed(143)

KEYS25 = [k for k in "qwertyuiopasdfghjklzxcvbnm" if k != "p"]

jd1 = yaml.safe_load(open(BASE / "data/jdhe/简单鹤初稿20240512.yaml", encoding="utf-8"))
jd1_map = {str(k): v for k, v in jd1["form"]["mapping"].items()}

roots = [l.strip() for l in open(WORK / "seed_roots.txt", encoding="utf-8") if l.strip()]
pairs = [l.rstrip("\n").split("\t") for l in open(WORK / "attachments_final.tsv", encoding="utf-8")][1:]
attached = {a: h for a, h in pairs}
mains = [r for r in roots if r not in attached]

mapping = {}
space = {}
# 音码：钉死
for k, v in jd1_map.items():
    if k.startswith("szm-") or k.startswith("mzm-"):
        mapping[k] = v
        space[k] = [{"value": v, "score": 0.0}]
# 主根：25 键空间 + 热启动
for r in mains:
    warm = jd1_map.get(r)
    if not isinstance(warm, str) or warm == "p":
        warm = random.choice(KEYS25)
    mapping[r] = warm
    space[r] = [{"value": k, "score": 0.0} for k in KEYS25]
# 附属形 + '6'
for a, h in attached.items():
    mapping[a] = {"element": h}
    space[a] = [{"value": {"element": h}, "score": 0.0}]
mapping["6"] = {"element": "5"}
space["6"] = [{"value": {"element": "5"}, "score": 0.0}]

cfg = {
    "version": "0.4",
    "source": None,
    "info": {"name": "夜莺码", "author": "nightingale", "version": "0.1",
             "description": "143根 音形方案 · 小鹤双拼 · 字根不落p键"},
    "form": {
        "alphabet": "qwertyuiopasdfghjklzxcvbnm",
        "mapping_type": 1,
        "mapping": mapping,
        "mapping_space": space,
    },
    "encoder": {
        "max_length": 4,
        "select_keys": ["_", ";"],
        "auto_select_length": 4,
        "sources": jd1["encoder"]["sources"],
        "conditions": jd1["encoder"]["conditions"],
        "short_code": [{"length_equal": 1, "schemes": [{"prefix": 3}]}],
        "rules": jd1["encoder"]["rules"],
    },
    "optimization": {
        "objective": jd1["optimization"]["objective"],
        "metaheuristic": {"algorithm": "SimulatedAnnealing"},
    },
}
yaml.safe_dump(cfg, open(OUT / "config.yaml", "w", encoding="utf-8"), allow_unicode=True, sort_keys=False, width=10000)

# 词信息文件：8454 条单字（v176 拆分）
items = []
for line in open(WORK / "v176_assembled.tsv", encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) < 3 or len(p[0]) != 1:
        continue
    seq = []
    ok = True
    for tok in p[1].split(" "):
        try:
            e = json.loads(tok)
        except json.JSONDecodeError:
            ok = False
            break
        if isinstance(e, dict):
            seq.append({"element": e["element"], "index": e.get("index", 0)})
        else:
            seq.append(str(e))
    if ok and seq:
        items.append({"词": p[0], "元素序列": seq, "频率": int(p[2])})
yaml.safe_dump(items, open(OUT / "elements.yaml", "w", encoding="utf-8"), allow_unicode=True, sort_keys=False, width=10000)
print(f"config.yaml: {len(mapping)} 元素映射, 决策空间 {len(space)}（其中可动 {len(mains)+5} 个 × 25 键）")
print(f"elements.yaml: {len(items)} 条")
