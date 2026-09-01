# -*- coding: utf-8 -*-
"""夜莺码留位版搜狗短语生成器（搭档搜狗自带双拼词库使用）。

思路: 我们不放词——搜狗原生双拼负责出词。对每个四码位:
  若 max(该码位词频) > 首选字的独立频率(字频×独立率) → 整组字从第2选起步, 第1选留空给搜狗的词
  否则字保持第1选(单飞字保护)
简码位(1-3码)不变——形码字优先本来就是设计意图。
输出: releases/v0.3.1/夜莺码v0.4留位版搜狗短语.txt
"""
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
REL = BASE / "releases/v0.4"

readings = json.load(open(BASE / "work/readings.json", encoding="utf-8"))
cfreq = {c: rs[0][0] for c, rs in readings.items()}

wfreq = {}
for line in open(BASE / "repos/webchai/packages/hanzi-chai/src/data/dictionary.txt", encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) >= 3 and len(p[0]) >= 2:
        try:
            wfreq[p[0]] = max(wfreq.get(p[0], 0), int(p[2]))
        except ValueError:
            pass
# 每码位最强词频（大词库全量编码版）; code_shortword=该码位存在<4字的活词（字数优先规则用）
code_wmax = defaultdict(int)
code_shortword = set()
for line in open(BASE / "work/夜莺码_大词库编码版.txt", encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) >= 2:
        f = wfreq.get(p[0], 0)
        if f > code_wmax[p[1]]:
            code_wmax[p[1]] = f
        if len(p[0]) < 4:
            code_shortword.add(p[1])  # 不问词频: 搜狗原生可能有本地词频表没有的短词(很远案)
# 独立率
inword = defaultdict(int)
for w, f in wfreq.items():
    for c in set(w):
        inword[c] += f
def standalone(c):
    tf = cfreq.get(c, 0)
    return max(0, tf - inword.get(c, 0))

# 读入现行搜狗表（已含基础+补丁+扩展、统一编号），按码重组
by_code = defaultdict(list)
t = open(REL / "夜莺码v0.4搜狗自定义短语.txt", encoding="utf-16").read()
for l in t.split("\n"):
    l = l.strip()
    if l.startswith(";") or "=" not in l or "," not in l:
        continue
    cp, w = l.split("=", 1)
    code, pos = cp.rsplit(",", 1)
    by_code[code].append((int(pos), w))

# ---- 简词层·法典2.0: 金卡无条件 + 撞车词恩公打包 + 双上限(总3/非金卡2) ----
main = {c: rs[0][1] for c, rs in readings.items()}
words_sorted = []
for line in open(BASE / "work/夜莺码_词库17万瘦身版.txt", encoding="utf-8"):
    p = line.rstrip().split(chr(9))
    if len(p) >= 2 and wfreq.get(p[0], 0) > 0:
        words_sorted.append((wfreq[p[0]], p[0], p[1]))
words_sorted.sort(reverse=True)
def wcode(w):
    cs = [main.get(c) for c in w]
    if any(x is None for x in cs):
        return None
    if len(w) == 2:
        return cs[0][:2] + cs[1][:2]
    if len(w) == 3:
        return cs[0][0] + cs[1][0] + cs[2][0] + cs[2][1]
    return cs[0][0] + cs[1][0] + cs[2][0] + cs[3][0]
def jp(w, code):
    if len(w) == 2:
        return code[0] + code[2]
    if len(w) == 3:
        return code[:3]
    return None
fullcode_count = defaultdict(int)
wc_cache = {}
for f, w, _ in words_sorted:
    c = wcode(w)
    wc_cache[w] = c
    if c:
        fullcode_count[c] += 1
colliding = {w for w, c in wc_cache.items() if c and fullcode_count[c] >= 2}
# 金卡前100(剔年月); 排名表
gold = []
rankmap = {}
r = 0
for f, w, _ in words_sorted:
    if w == "年月":
        continue
    r += 1
    rankmap[w] = r
    if r <= 100:
        gold.append(w)
gold_set = set(gold)
# 每简拼位: 该位所有词按频率序(用于找恩公)
at_jp = defaultdict(list)
for f, w, code in words_sorted:
    j = jp(w, code)
    if j:
        at_jp[j].append(w)   # 已按频率降序
# 有字码位: 上限各减一
short_char_at = set()
for line in open(REL / "夜莺码v0.4纯单版.txt", encoding="utf-8"):
    q = line.rstrip().split(chr(9))
    if len(q) >= 2 and len(q[1]) in (2, 3):
        short_char_at.add(q[1])
jw_add = defaultdict(list)
jw_nongold = defaultdict(int)
# 1) 金卡入驻
n_gold_in = 0
for j, ws in at_jp.items():
    for w in ws:
        if w in gold_set:
            jw_add[j].append(w)
            n_gold_in += 1
# 2) 撞车词按频率序处理, 恩公打包 + 双上限
n2 = n3 = 0
for f, A, code in words_sorted:
    j = jp(A, code)
    if not j or A in gold_set or rankmap.get(A, 99999) > 5000 or A not in colliding:
        continue
    if A in jw_add[j]:
        continue
    # 恩公: 该位频率高于A、排名>100、尚未入驻的最高频词
    escort = None
    for w2 in at_jp[j]:
        if w2 == A:
            break
        if w2 in gold_set or w2 in jw_add[j]:
            continue
        escort = w2
        break
    package = ([escort] if escort else []) + [A]
    cap_total = 2 if j in short_char_at else 3
    cap_nongold = 1 if j in short_char_at else 2
    if len(jw_add[j]) + len(package) > cap_total or jw_nongold[j] + len(package) > cap_nongold:
        continue
    for w2 in package:
        jw_add[j].append(w2)
        jw_nongold[j] += 1
        if len(w2) == 2:
            n2 += 1
        else:
            n3 += 1
jw_add = dict(jw_add)
print(f"简词法典2.0: 金卡入位 {n_gold_in} / 二简 {n2} / 三简 {n3}")
# 特殊简词: 什么家族 s 镜像(仅镜像已持简拼者)
mirror_targets = defaultdict(list)
for j, ws in list(jw_add.items()):
    for w in ws:
        if "什么" in w:
            alt = "".join("s" if c == "什" else main[c][0] for c in w)
            if alt != j:
                mirror_targets[alt].append(w)
n_mir = 0
for alt, ws in mirror_targets.items():
    for w in ws:
        if w not in jw_add.get(alt, []):
            jw_add.setdefault(alt, []).append(w)
            n_mir += 1
print(f"什么家族 s 镜像: {n_mir} 条")

# 四字词简拼（声母×4）：冲突排全码单字后、扩展字前；空位坐首选
idioms = defaultdict(list)
sy_path = BASE / "work/四字词精选.txt"
if sy_path.exists():
    tmp = []
    for line in open(sy_path, encoding="utf-8"):
        w = line.strip()
        if len(w) == 4 and all(c in main for c in w):
            code = "".join(main[c][0] for c in w)
            tmp.append((wfreq.get(w, 0), w, code))
    tmp.sort(reverse=True)
    for f, w, code in tmp:
        idioms[code].append(w)
    print(f"四字词简拼: {sum(len(v) for v in idioms.values())} 条 / {len(idioms)} 码位")
ext_chars = set()
ext_file = BASE / "work/扩展字集_打字版.tsv"
if ext_file.exists():
    for line in open(ext_file, encoding="utf-8"):
        q = line.rstrip().split(chr(9))
        if len(q) >= 2:
            ext_chars.add(q[0])

lines = ["; 夜莺码 v0.3.1 留位版 · 搜狗自定义短语（配搜狗原生小鹤双拼出词）",
         "; 四码位: 词频>首字独立频率 → 字从第2选起步, 第1选留给搜狗原生词",
         "; 简词: 空位第1选, 撞位次选借位", ""]
demoted = kept = 0
samples = []
total = 0
for code in sorted(by_code):
    cands = sorted(by_code[code])
    offset = 0
    if len(code) == 4:
        head = cands[0][1]
        # 词压字门槛1万: 低频词(如香樟3719压项141万)无权夺首选（2026-08-20 用户裁定）
        if len(head) == 1 and code_wmax.get(code, 0) > standalone(head) and code_wmax.get(code, 0) >= 10000:
            offset = 1
            demoted += 1
            if len(samples) < 10:
                samples.append(f"{code}: {''.join(w for _, w in cands[:3])}→2起")
        elif len(head) == 1:
            kept += 1
    emitted = []
    ext_tail = [w for _, w in cands if len(w) == 1 and w in ext_chars]
    front = [w for _, w in cands if not (len(w) == 1 and w in ext_chars)]
    queue = front + idioms.pop(code, []) + ext_tail
    for w in queue:
        if w in emitted:
            continue
        lines.append(f"{code},{len(emitted) + offset + 1}={w}")
        emitted.append(w)
        total += 1
    for w in jw_add.pop(code, []):
        if w in emitted:
            continue
        lines.append(f"{code},{len(emitted) + offset + 1}={w}")
        emitted.append(w)
        total += 1
# 全空码位的四字词：先过留位对决（字数优先：该码位有短词一律让1号给搜狗；同为四字才比词频）
for code in sorted(idioms):
    ws = list(dict.fromkeys(idioms[code]))
    off = 1 if (code in code_shortword or code_wmax.get(code, 0) > max(wfreq.get(w, 0) for w in ws)) else 0
    for i, w in enumerate(ws, 1):
        lines.append(f"{code},{i + off}={w}")
        total += 1
# 全空码位的简词（免费地皮）
for code in sorted(jw_add):
    for i, w in enumerate(dict.fromkeys(jw_add[code]), 1):
        lines.append(f"{code},{i}={w}")
        total += 1
open(REL / "夜莺码v0.4留位版搜狗短语.txt", "wb").write(("\r\n".join(lines) + "\r\n").encode("utf-16"))
print(f"留位版: {total} 条；四码位让位 {demoted} 个 / 保位 {kept} 个")
print("让位示例:", " ".join(samples))
