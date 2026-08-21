# -*- coding: utf-8 -*-
"""夜莺码词版搜狗短语生成器。

排序法典（每个四码位）：
  受保护无简码字(独立率>50%) → 词(按词频) → 让位无简码字(独立率≤50%) → 有简码字全码备胎 → 扩展字
简词层：
  一简词: 每字母第3选放最高频二字词（一简字占1-2）
  二简词: 二字词声母简拼——空位首选进驻，撞二简字则次选借位
  三简词: 三字词声母简拼——排在三简字之后
预算: 搜狗上限10万条。词取前 TOP_WORDS 条。
输出: releases/v0.4/夜莺码v0.4字词总表.txt + 复核清单（搜狗挂接见 make_liuwei.py 留位版）
"""
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
REL = BASE / "releases/v0.4"
TOP_WORDS = 50000
N_JW2 = 1500   # 二简词数量上限
N_JW3 = 5000   # 三简词数量上限

# ---- 基础数据 ----
readings = json.load(open(BASE / "work/readings.json", encoding="utf-8"))
cfreq = {c: rs[0][0] for c, rs in readings.items()}
main = {c: rs[0][1] for c, rs in readings.items()}

wfreq = {}
for line in open(BASE / "repos/webchai/packages/hanzi-chai/src/data/dictionary.txt", encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) >= 3 and len(p[0]) >= 2:
        try:
            wfreq[p[0]] = max(wfreq.get(p[0], 0), int(p[2]))
        except ValueError:
            pass
words = []
for line in open(BASE / "work/夜莺码_词库17万瘦身版.txt", encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) >= 2 and wfreq.get(p[0], 0) > 0:
        words.append((wfreq[p[0]], p[0], p[1]))
words.sort(reverse=True)
words = words[:TOP_WORDS]

# 独立率
inword = defaultdict(int)
for w, f in wfreq.items():
    for c in set(w):
        inword[c] += f
def indep(c):
    tf = cfreq.get(c, 0)
    return max(0, tf - inword.get(c, 0)) / tf if tf else 1.0
def standalone(c):
    tf = cfreq.get(c, 0)
    return max(0, tf - inword.get(c, 0))
code_wmax = defaultdict(int)
for line in open(BASE / "work/夜莺码_大词库编码版.txt", encoding="utf-8"):
    p2 = line.rstrip().split(chr(9))
    if len(p2) >= 2:
        f2 = wfreq.get(p2[0], 0)
        if f2 > code_wmax[p2[1]]:
            code_wmax[p2[1]] = f2

# ---- 读入现有纯单表（含扩展），按码分组并标注层级 ----
# 层级: 0=无简码字(待按独立率分裂) 1=有简码字备胎 9=扩展字; 简码条目(码长<4)原样保留
shortest = {}
rows = []
for line in open(REL / "夜莺码v0.4纯单版.txt", encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) >= 2:
        rows.append((p[0], p[1]))
        c = p[0]
        if c not in shortest or len(p[1]) < len(shortest[c]):
            shortest[c] = p[1]
base_chars = set(c for c, rs in readings.items())
by_code = defaultdict(list)   # code -> [(层级, sub, 词条)]
for c, code in rows:
    if len(code) < 4:
        by_code[code].append((0, -cfreq.get(c, 0), c))
        continue
    is_ext = c not in base_chars
    has_short = len(shortest.get(c, "xxxx")) < 4
    if is_ext:
        tier = 9.0
    elif has_short:
        tier = 5.0
    else:
        # 与留位版同式: 实战对决 词频 vs 字独立频率；词压字门槛1万（低频词无权夺首选）
        _wm = code_wmax.get(code, 0)
        tier = 0.0 if (standalone(c) >= _wm or _wm < 10000) else 3.0
    by_code[code].append((tier, -cfreq.get(c, 0), c))

review = []
for c in base_chars:
    if len(shortest.get(c, "xxxx")) >= 4:
        r = indep(c)
        if 0.05 <= r <= 0.5:
            review.append((r, c))

# ---- 词全码进场（层级 2.0，字词同位则按法典排） ----
# 同码位词排序: 字数优先于词频（短词在前，四字词垫后，2026-08-20 用户裁定）
for f, w, code in words:
    by_code[code].append((2.0, (len(w), -f), w))

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

# 简词写入 (tier 6, 保持法典2.0顺序)
for jw2, ws2 in jw_add.items():
    for idx2, w2 in enumerate(ws2):
        by_code[jw2].append((6.0, idx2, w2))

# 四字词简拼(声母×4) tier 8.5
n_j4 = 0
sy = BASE / "work/四字词精选.txt"
if sy.exists():
    for line in open(sy, encoding="utf-8"):
        w = line.strip()
        if len(w) == 4 and all(c in main for c in w):
            code = "".join(main[c][0] for c in w)
            by_code[code].append((8.5, -wfreq.get(w, 0), w))
            n_j4 += 1
print(f"四字词简拼: {n_j4}")

# ---- 补丁（快符/补码/备用码） ----
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
    for l in st.splitlines():
        l = l.strip()
        if l.startswith(";") or "=" not in l or "," not in l:
            continue
        cp, w = l.split("=", 1)
        code, pos = cp.rsplit(",", 1)
        by_code[code].append((1.0 + int(pos) * 0.01, 0, w))

# ---- 输出 ----
# 搜狗挂接由留位版(make_liuwei.py)承担；本脚本只出普通格式总表（群查询/赛码用，无条数上限）
# 普通格式总表（词\t码，行序=候选序）：群机器人查询/赛码器用
plain = []
for code in sorted(by_code):
    seen = set()
    for tier, negf, w in sorted(by_code[code]):
        if w in seen:
            continue
        seen.add(w)
        plain.append(f"{w}\t{code}")
open(REL / "夜莺码v0.4字词总表.txt", "w", encoding="utf-8", newline="\n").write("\n".join(plain) + "\n")
print(f"字词总表(普通格式): {len(plain)} 条")
with open(BASE / "work/独立率复核清单.tsv", "w", encoding="utf-8") as f:
    f.write("字\t独立率\t说明: 5%~50%灰色区,当前默认保护(字在词前),可手工改判\n")
    for r, c in sorted(review):
        f.write(f"{c}\t{r*100:.1f}%\n")
print(f"独立率灰色区复核清单: {len(review)} 字 → work/独立率复核清单.tsv")
