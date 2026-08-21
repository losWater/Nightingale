# -*- coding: utf-8 -*-
"""夜莺码正式码表生成器 v0.2.1
主码 = 频率最高的读音（修复多音字次读音抢简码 bug）
政策: 单重简码(一/二/三简) + 护指加成×3(末码 iklo) + 出简出全 + 让全 + 多音字全码保留
输出: releases/v0.2/夜莺码v0.3纯单版.txt、搜狗自定义短语、查码页数据同步重生成
"""
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
REL = BASE / "work/repro_test"

readings = json.load(open(BASE / "work/readings.json", encoding="utf-8"))  # 字 -> [[freq,code]...] 频率降序
DANGER = set("iklo")
BOOST = 3

chars = sorted(readings, key=lambda c: -readings[c][0][0])
main = {c: readings[c][0][1] for c in chars}
freq = {c: readings[c][0][0] for c in chars}

assigned = {}
for L in (1, 2, 3):
    bucket = defaultdict(list)
    for c in chars:
        if c in assigned:
            continue
        bucket[main[c][:L]].append(c)
    for prefix, cands in bucket.items():
        # 护指加成只在三简层生效：一二简凭纯字频，最后的救生艇才优先安置危险结尾字
        boost_on = (L == 3)
        cands.sort(key=lambda c: -freq[c] * (BOOST if boost_on and main[c][-1] in DANGER else 1))
        assigned[cands[0]] = prefix

entries = []
for c in chars:
    codes = [code for f, code in readings[c]]
    seen = set()
    codes = [x for x in codes if not (x in seen or seen.add(x))]
    if c in assigned:
        entries.append((assigned[c], 0, -freq[c], c))
        for fc in codes:
            entries.append((fc, 1, -freq[c], c))
    else:
        for fc in codes:
            entries.append((fc, 0, -freq[c], c))
# 扩展字集（末位公民：全码 only、永居本码位队尾、二选起步）
ext_path = BASE / "work/扩展字集_打字版.tsv"
if ext_path.exists():
    n_ext = 0
    for line in open(ext_path, encoding="utf-8"):
        q = line.rstrip("\n").split("\t")
        if len(q) >= 2:
            entries.append((q[1], 2, 0, q[0]))
            n_ext += 1
    print(f"扩展字集并入 {n_ext} 条")
entries.sort()
with open(REL / "夜莺码v0.3纯单版.txt", "w", encoding="utf-8", newline="\n") as f:
    for code, y, negf, c in entries:
        f.write(f"{c}\t{code}\n")

# 统计
total_f = sum(freq.values()) or 1
wkl = sum((len(assigned.get(c, main[c])) + 1) * freq[c] for c in chars) / total_f
lv = defaultdict(int)
for c, pre in assigned.items():
    lv[len(pre)] += 1
print(f"条目 {len(entries)}；一/二/三简 {lv[1]}/{lv[2]}/{lv[3]}；加权键长 {wkl:.3f}")

# 搜狗自定义短语：统一排队（基础字→补丁→扩展字），顺序编号杜绝位次冲突
by_code = defaultdict(list)   # code -> [(层级, 词)]
order = []
for code, y, negf, c in entries:
    if code not in by_code:
        order.append(code)
    by_code[code].append((y if y < 2 else 9, c))  # 扩展字层级 9 保证垫底
for patchname in ("symbo.txt", "补码.txt", "备用码.txt"):
    pf = BASE / patchname
    if not pf.exists():
        continue
    raw = pf.read_bytes()
    for enc in ("utf-8-sig", "utf-16", "gbk"):
        try:
            st = raw.decode(enc)
            break
        except UnicodeDecodeError:
            pass
    n_sym = 0
    for l in st.splitlines():
        l = l.strip()
        if l.startswith(";") or "=" not in l or "," not in l:
            continue
        cp, w = l.split("=", 1)
        code, pos = cp.rsplit(",", 1)
        if code not in by_code:
            order.append(code)
        by_code[code].append((2 + int(pos) * 0.01, w))  # 补丁层级 2.x，按声明位次相对排序
        n_sym += 1
    print(f"{patchname} 并入 {n_sym} 条")
lines = ["; 夜莺码 v0.3.1 纯单版 · 搜狗自定义短语挂接", "; 字词混合退火布局 · 52附属形 · 单重简码+护指2.0 · 出简出全 · 快符/补码/备用码/扩展字集", ""]
total_entries = 0
for code in sorted(order):
    cands = sorted(by_code[code], key=lambda x: x[0])
    for i, (_, w) in enumerate(cands, 1):
        lines.append(f"{code},{i}={w}")
        total_entries += 1
open(REL / "夜莺码v0.3搜狗自定义短语.txt", "wb").write(("\r\n".join(lines) + "\r\n").encode("utf-16"))
print(f"搜狗短语 {total_entries} 条")

# 抽查
for probe in ("uv", "uo", "xk", "hh", "di", "de"):
    print(f"  {probe}: {''.join(w for _, w in sorted(by_code.get(probe, [])))}")
