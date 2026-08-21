# -*- coding: utf-8 -*-
"""readings 与 v04 拆分对账：按现行拆分计算应有码，缺失则补（双码），无简码且赢得新前缀者换主码。"""
import io
import json
import sys
from pathlib import Path

import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent

cfg = yaml.safe_load(open(BASE / "releases/v0.4/夜莺码v0.4键位布局.yaml", encoding="utf-8"))
mains = {}
attach = {}
for k, v in cfg["form"]["mapping"].items():
    k = str(k)
    if k.startswith(("szm-", "mzm-")):
        continue
    if isinstance(v, str):
        mains[k] = v
    else:
        attach[k] = str(v["element"])

def key_of(r, d=0):
    if r in mains:
        return mains[r]
    if r in attach and d < 4:
        return key_of(attach[r], d + 1)
    return None

splits = {}
for line in open(BASE / "work/v04_final.tsv.splits.tsv", encoding="utf-8"):
    c, _, rest = line.rstrip("\n").partition("\t")
    if len(c) == 1 and c not in splits:
        splits[c] = rest.split(" ")

readings = json.load(open(BASE / "work/readings.json", encoding="utf-8"))
freq = {c: rs[0][0] for c, rs in readings.items()}
full = {}
short = {}
for line in open(BASE / "releases/v0.4/夜莺码v0.4纯单版.txt", encoding="utf-8"):
    c, _, cd = line.strip().partition("\t")
    full.setdefault(cd, []).append(c)
    if c in readings and (c not in short or len(cd) < len(short[c])):
        short[c] = cd

def untouchable(p):
    hs = [x for x in full.get(p, []) if x in readings]
    if not hs:
        return None, False
    w1 = hs[0]
    w1f = [cd for cd, chs in full.items() if w1 in chs and len(cd) == 4]
    dup = any(len([x for x in full[cd] if x in readings]) > 1 for cd in w1f)
    return w1, dup

n_new = 0
gainers = []
for c in readings:
    sh = splits.get(c)
    if not sh:
        continue
    k1, k2 = key_of(sh[0]), key_of(sh[-1])
    if not (k1 and k2):
        continue
    cur = [x[1] for x in readings[c]]
    newpairs = []
    for f, cd in readings[c]:
        if len(cd) != 4:
            continue
        nc = cd[:2] + k1 + k2
        if nc not in cur and nc not in [x[1] for x in newpairs]:
            newpairs.append([f, nc])
    if not newpairs:
        continue
    n_new += len(newpairs)
    win = False
    if len(short.get(c, "xxxx")) >= 4:
        p = newpairs[0][1][:3]
        w1, unt = untouchable(p)
        if w1 is None:
            win = True
        elif not unt and freq.get(c, 0) > freq.get(w1, 0):
            win = True
    if win:
        readings[c] = newpairs + readings[c]
        gainers.append(c)
    else:
        readings[c] = readings[c] + newpairs

json.dump(readings, open(BASE / "work/readings.json", "w", encoding="utf-8"), ensure_ascii=False)
print("补码", n_new, "条; 换主码赢家:", "".join(gainers))
