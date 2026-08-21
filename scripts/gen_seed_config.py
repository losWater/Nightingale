# -*- coding: utf-8 -*-
"""生成夜莺码种子配置：jd1_repro 为模板，字根换成投票共识（≥3票）。

- 笔画根 一丨丿丶乙 折算为分类元素 '1'-'5'（另配 '6'→'5' 附挂）
- 字根键位阶段无关，先全部挂在占位键上
- 弃用 jd1 的 customize（绑定旧根表）；音码 szm/mzm 原样保留
用法: python gen_seed_config.py [--min-votes 3] [--out work/seed.yaml]
"""
import argparse
import io
import sys
import yaml
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent

STROKE_FOLD = {"一": "1", "丨": "2", "丿": "3", "丶": "4", "乙": "5"}

ap = argparse.ArgumentParser()
ap.add_argument("--min-votes", type=float, default=3.0)
ap.add_argument("--out", default="work/seed.yaml")
ap.add_argument("--roots-out", default="work/seed_roots.txt")
a = ap.parse_args()

rows = [l.rstrip("\n").split("\t") for l in open(BASE / "work/vote_matrix.tsv", encoding="utf-8")][1:]
roots = []
for r in rows:
    if float(r[2]) >= a.min_votes:
        c = r[0]
        c = STROKE_FOLD.get(c, c)
        if c not in roots:
            roots.append(c)
for s in "12345":
    if s not in roots:
        roots.append(s)

cfg = yaml.safe_load(open(BASE / "work/jd1_repro.yaml", encoding="utf-8"))
cfg["info"] = {"name": "夜莺码种子", "author": "nightingale", "version": "seed-0.1",
               "description": "C阶段共识根种子（键位未优化）"}

old_mapping = cfg["form"]["mapping"]
new_mapping = {}
for k, v in old_mapping.items():
    k = str(k)
    if k.startswith("szm-") or k.startswith("mzm-"):
        new_mapping[k] = v
# 字根全部挂占位键（键位无关阶段）
for i, r in enumerate(roots):
    new_mapping[r] = "abcdefghijklmnostuvwxyz"[i % 23]  # 避开 p/q/r? 只是占位，均匀散开即可
new_mapping["6"] = {"element": "5"}
cfg["form"]["mapping"] = new_mapping
cfg["form"]["alphabet"] = "qwertyuioasdfghjklzxcvbnm"  # 25 键，无 p

if "customize" in cfg.get("analysis", {}):
    del cfg["analysis"]["customize"]

yaml.safe_dump(cfg, open(BASE / a.out, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False, width=10000)
open(BASE / a.roots_out, "w", encoding="utf-8").write("\n".join(roots))
print(f"种子字根 {len(roots)} 个（含笔画根5个）→ {a.out}")
