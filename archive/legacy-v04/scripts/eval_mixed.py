# -*- coding: utf-8 -*-
"""字词实战评测：字词同台按频率排候选，统计词/全码字的非首选率。

测评站的词组测评只数词-词碰撞，看不见字词互撞——这杆秤才是真实输入体验口径。
规则：有简码的字走简码（短码不与四码词竞争，免疫）；全码字与词在四码空间同台，
频率高者居前（字频词频同源 chai dictionary，可比）。

用法: python eval_mixed.py <assembled.tsv> <layout.yaml> [名称]
例:   python eval_mixed.py work/v03_assembled.tsv releases/v0.3/夜莺码v0.3键位布局.yaml v0.3
"""
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent

def main():
    assembled, layout = sys.argv[1], sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else layout

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
            words.append((p[0], p[1], wfreq[p[0]]))
    words.sort(key=lambda x: -x[2])

    m = {str(k): v for k, v in yaml.safe_load(open(layout, encoding="utf-8"))["form"]["mapping"].items()}
    def key_of(e):
        v = m.get(e)
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            return key_of(str(v["element"]))
        return None
    readings = defaultdict(list)
    for line in open(assembled, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 3 or len(p[0]) != 1:
            continue
        elems = [json.loads(t)["element"] for t in p[1].split(" ")]
        keys = [key_of(e) for e in elems]
        if None in keys or len(keys) != 4:
            continue
        f = int(p[2])
        code = "".join(keys)
        if (f, code) not in readings[p[0]]:
            readings[p[0]].append((f, code))
    for c in readings:
        readings[c].sort(reverse=True)

    freq = {c: rs[0][0] for c, rs in readings.items()}
    mainc = {c: rs[0][1] for c, rs in readings.items()}
    chars = sorted(readings, key=lambda c: -freq[c])
    DANGER = set("iklo")
    assigned = {}
    for L in (1, 2, 3):
        bucket = defaultdict(list)
        for c in chars:
            if c in assigned:
                continue
            bucket[mainc[c][:L]].append(c)
        for prefix, cands in bucket.items():
            cands.sort(key=lambda c: -freq[c] * (3 if L == 3 and mainc[c][-1] in DANGER else 1))
            assigned[cands[0]] = prefix

    slot = defaultdict(list)
    for c in readings:
        if c not in assigned:
            slot[mainc[c]].append(("字", c, freq[c]))
    for w, code, f in words:
        slot[code].append(("词", w, f))
    for k in slot:
        slot[k].sort(key=lambda x: -x[2])

    total_wf = sum(f for _, _, f in words) or 1
    w_tax = top2000_bad = blocked_by_char = 0
    for i, (w, code, f) in enumerate(words):
        rank = [x[1] for x in slot[code]].index(w)
        if rank > 0:
            w_tax += f
            if i < 2000:
                top2000_bad += 1
            if any(t == "字" for t, _, _ in slot[code][:rank]):
                blocked_by_char += 1
    fullchars = [c for c in readings if c not in assigned]
    total_cf = sum(freq[c] for c in fullchars) or 1
    c_tax = sum(freq[c] for c in fullchars if [x[1] for x in slot[mainc[c]]].index(c) > 0)
    print(f"== {name} ==")
    print(f"  词非首选(词频加权): {w_tax/total_wf*100:.2f}%  前2000词非首选: {top2000_bad}  被字挡词位: {blocked_by_char}")
    print(f"  全码字非首选(字频加权): {c_tax/total_cf*100:.2f}%  (全码字 {len(fullchars)} 个)")

if __name__ == "__main__":
    main()
