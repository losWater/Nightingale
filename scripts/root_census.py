# -*- coding: utf-8 -*-
"""字根就业普查：动根后体检用。
报告：真幽灵（本尊+附属合计零就业）、门面根（本尊零、附属撑）、个位数就业根、只进中部的根。
附属就业记到宿主头上（止/E437 分工是正常形态，不报假警）。"""
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
STROKES = set("123456㇒㇏")

readings = json.load(open(BASE / "work/readings.json", encoding="utf-8"))
freq = {c: rs[0][0] for c, rs in readings.items()}
splits = {}
for line in open(BASE / "work/v04_final.tsv.splits.tsv", encoding="utf-8"):
    c, _, rest = line.rstrip("\n").partition("\t")
    if len(c) == 1 and c not in splits:
        splits[c] = rest.split(" ")

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

def host(r, d=0):
    if r in mains or d > 3:
        return r
    return host(attach[r], d + 1) if r in attach else r

def label(r):
    return r if r.strip() and not (0xE000 <= ord(r[0]) <= 0xF8FF) else "PUA" + hex(ord(r[0]))[2:]

use = defaultdict(lambda: [0, 0, 0, 0])  # 本尊字数, 家族字数, 码位字数, 频和
for c, sh in splits.items():
    if c not in freq:
        continue
    for r in set(sh):
        use[r][0] += 1
        use[r][3] += freq[c]
        if sh[0] == r or sh[-1] == r:
            use[r][2] += 1
        h = host(r)
        if h != r:
            use[h][1] += 1

print("== 真幽灵（本尊+附属合计零就业）==")
n = 0
for r, key in mains.items():
    if r in STROKES:
        continue
    if use[r][0] + use[r][1] == 0:
        print(" ", label(r), key)
        n += 1
print("  无" if n == 0 else f"  共{n}个")

print("== 门面根（本尊零就业，附属撑场）==")
for r, key in mains.items():
    if r in STROKES:
        continue
    if use[r][0] == 0 and use[r][1] > 0:
        ats = "".join(label(a) for a, _ in attach.items() if host(a) == r)
        print(f"  {label(r)}({key}) 附属[{ats}] 家族{use[r][1]}字")

print("== 个位数就业根（家族≤9字）==")
for r, key in sorted(mains.items(), key=lambda kv: use[kv[0]][0] + use[kv[0]][1]):
    if r in STROKES:
        continue
    fam = use[r][0] + use[r][1]
    if 0 < fam <= 9:
        print(f"  {label(r)}({key}) {fam}字 频{use[r][3] // 10000}万")

print("== 只进中部、从不进码位的根 ==")
n = 0
for r, key in mains.items():
    if r in STROKES:
        continue
    if use[r][0] > 0 and use[r][2] == 0:
        print(f"  {label(r)}({key}) {use[r][0]}字全在中部")
        n += 1
print("  无" if n == 0 else "")
