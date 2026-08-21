# -*- coding: utf-8 -*-
"""指法统计（按《科学形码测评体系》定义）：互击/同指大小跨排/小指干扰/同键连击。
用法: python fingering.py <code.txt> [<code2.txt> ...]  （chai 输出格式，取全码列）"""
import io
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent

ROWS = ["qwertyuiop", "asdfghjkl;", "zxcvbnm"]
POS = {}
for r, row in enumerate(ROWS):
    for c, ch in enumerate(row):
        POS[ch] = (r, c)
# 手指: 0小1无2中3食 (标准指法)
def finger(ch):
    r, c = POS[ch]
    col = c if r < 2 else c + 0  # z行错位近似
    if r == 2:
        col = c  # zxcvbnm: z=a列...近似 c
    hand = 0 if col <= 4 else 1
    f = {0: 0, 1: 1, 2: 2, 3: 3, 4: 3, 5: 3, 6: 3, 7: 2, 8: 1, 9: 0}.get(col, 0)
    return hand, f, r, col

def classify(a, b):
    if a not in POS or b not in POS:
        return "其他"
    h1, f1, r1, c1 = finger(a)
    h2, f2, r2, c2 = finger(b)
    if a == b:
        return "同键"
    if h1 != h2:
        return "互击"
    if f1 == f2:
        return "大跨排" if abs(r1 - r2) >= 2 else "小跨排"
    # 小指干扰: 同手内 小指 与 无名/中指 共用
    if (f1 == 0 and f2 in (1, 2)) or (f2 == 0 and f1 in (1, 2)):
        return "小指干扰"
    return "同手其他"

freq = {}
for line in open(BASE / "work/v176_assembled.tsv", encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) >= 3 and len(p[0]) == 1:
        freq[p[0]] = max(freq.get(p[0], 0), int(p[2]))

for path in sys.argv[1:]:
    stats = defaultdict(float)
    triple_same_key = 0.0
    total = 0.0
    seen = set()
    for line in open(path, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 2 or len(p[0]) != 1 or p[0] in seen:
            continue
        seen.add(p[0])
        code, f = p[1], freq.get(p[0], 0)
        for i in range(len(code) - 1):
            stats[classify(code[i], code[i + 1])] += f
            total += f
        for i in range(len(code) - 2):
            if code[i] == code[i + 1] == code[i + 2]:
                triple_same_key += f
    name = Path(path).name
    print(f"== {name} ==")
    for k in ("互击", "小跨排", "大跨排", "同键", "小指干扰", "同手其他"):
        print(f"  {k}: {stats[k]/total*100:.2f}%")
    print(f"  同键三连(字频权重): {triple_same_key/total*100:.3f}%")
