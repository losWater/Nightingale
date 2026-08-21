# -*- coding: utf-8 -*-
"""加根择键器：实现 work/加根规则.md 的空位判定树。

规则一部件给定固定键；规则二部件沿 jfhgurytmvnbkdieclsowxaqz 遍历。
双码并存：旧码全保留，故无字会"卡死"；各键的账目为——
  gains3   头位部件才有：受影响字白捡/拼赢的三简（频率加权）
  demote   拼字频上位挤掉的在位简码持有者（频率加权，代价）
  messy    新全码落位后并非首选的字数（直观码打折，按层级排序后计）
停键判据：demote==0 且 messy==0 即"零残留"，沿序首个满足者即最优。
"""
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent

readings = json.load(open(BASE / "work/readings.json", encoding="utf-8"))
freq = {c: rs[0][0] for c, rs in readings.items()}
base = set(readings)

splits = {}
for line in open(BASE / "work/v031_final.tsv.splits.tsv", encoding="utf-8"):
    c, _, rest = line.rstrip("\n").partition("\t")
    if len(c) == 1 and c not in splits:
        splits[c] = rest.split(" ")

full = defaultdict(list)
short = {}
for line in open(BASE / "releases/v0.3.1/夜莺码v0.3.1纯单版.txt", encoding="utf-8"):
    c, _, cd = line.strip().partition("\t")
    full[cd].append(c)
    if c in base and (c not in short or len(cd) < len(short[c])):
        short[c] = cd

def tier(ch):
    if ch not in base:
        return 2
    return 1 if len(short.get(ch, "xxxx")) < 4 else 0

def first_of(cd, extra=None):
    occ = [(tier(x), -freq.get(x, 0), x) for x in full.get(cd, [])]
    if extra is not None:
        occ.append((tier(extra), -freq.get(extra, 0), extra))
    return sorted(occ)[0][2] if occ else None

def holder_untouchable(p):
    """三简位 p 的持有者是否为避重简码（其全码在基础字层有重）"""
    hs = full.get(p, [])
    if not hs:
        return None, False
    w1 = hs[0]
    w1_fulls = [cd for cd, chs in full.items() if w1 in chs and len(cd) == 4]
    dup = any(len([x for x in full[cd] if x in base]) > 1 for cd in w1_fulls)
    return w1, dup

def affected(pattern, where):
    """按笔画串匹配受影响字（基础字），返回 [(freq, char)]"""
    out = []
    for c, sh in splits.items():
        if c not in base or len(sh) < len(pattern):
            continue
        head = sh[: len(pattern)] == pattern
        tail = sh[-len(pattern):] == pattern
        whole = sh == pattern
        if (where == "head" and head) or (where == "tail" and tail) or (where == "any" and (head or tail)) or whole:
            pos = "whole" if whole else ("head" if head else "tail")
            out.append((freq[c], c, pos))
    out.sort(reverse=True)
    return out

def evaluate(name, pattern, where, keys, exclude=()):
    fam = [(f, c, pos) for f, c, pos in affected(pattern, where) if c not in exclude]
    print(f"\n== {name} == 受影响 {len(fam)} 字 总频 {sum(f for f,_,_ in fam)//10000} 万: "
          + "".join(c for _, c, _ in fam[:25]) + ("…" if len(fam) > 25 else ""))
    results = []
    for key in keys:
        gains3 = g3f = demote = messy = 0
        notes = []
        for f, c, pos in fam:
            olds = [cd for cd, chs in full.items() if c in chs and len(cd) == 4]
            if not olds:
                continue
            o = olds[0]
            if pos == "whole":
                nc = o[:2] + key + key
            elif pos == "head":
                nc = o[:2] + key + o[3]
            else:
                nc = o[:3] + key
            # messy: 新全码是否首选
            if first_of(nc, extra=c) != c:
                messy += 1
            # 三简（仅头位/整字，且本字尚无简码）
            if pos in ("head", "whole") and len(short.get(c, "xxxx")) >= 4:
                p = nc[:3]
                w1, unt = holder_untouchable(p)
                if w1 is None:
                    gains3 += 1; g3f += f
                elif not unt and freq.get(c, 0) > freq.get(w1, 0):
                    gains3 += 1; g3f += f
                    demote += freq.get(w1, 0)
                    notes.append(f"{c}挤{w1}")
        results.append((key, gains3, g3f, demote, messy, notes))
    for key, gains3, g3f, demote, messy, notes in results:
        flag = " ←零残留首中" if demote == 0 and messy == 0 else ""
        print(f"  键{key}: 捡三简{gains3}({g3f//10000}万) 挤位代价{demote//10000}万 新码非首选{messy}字 {';'.join(notes[:4])}{flag}")
        if demote == 0 and messy == 0:
            break

ORDER = list("jfhgurytmvnbkdieclsowxaqz")

CANDS = [
    ("龰(走是底)→止g[规则一]", ["2", "1", "3", "4"], "tail", ["g"], ()),
    ("戋→戈t[规则一]", ["二", "6", "㇒", "㇏"], "tail", ["t"], ("辰", "震", "振", "晨", "宸", "娠", "赈", "蜃")),
    ("象→豕v[规则一]", ["3", "5", "口", "㇒", "5", "㇒", "㇒", "㇒", "㇏"], "tail", ["v"], ()),
    ("成→戈t[规则一?]", ["厂", "5", "6", "㇒", "㇏"], "tail", ["t"], ()),
    ("艮[规则二]", ["彐", "6", "㇒", "㇏"], "tail", ORDER, ()),
    ("⺮(竹头)[规则二]", ["𠂉", "㇏", "𠂉", "㇏"], "head", ORDER, ()),
    ("弓[规则二]", ["5", "1", "5"], "head", ORDER, ()),
    ("母[规则二]", ["6", "5", "亠", "㇏"], "tail", ORDER, ()),
    ("及[规则二]", ["3", "5", "㇏"], "any", ORDER, ("久", "岛", "灸", "玖", "枭", "袅", "疚", "柩")),
    ("氐[规则二]", ["㇒", "6", "1", "6", "㇏"], "tail", ORDER, ()),
]

for name, pat, where, keys, exc in CANDS:
    evaluate(name, pat, where, keys, exc)
