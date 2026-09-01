# -*- coding: utf-8 -*-
"""v0.4 加根拆分变换模块 + 扩展字集双码追加（python scripts/v04_transform.py ext 执行扩展字处理）"""
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent

XT = ""  # 学字头
DT = ""  # 党字头

FAMS = [
    (["3", "5", "口", "㇒", "5", "㇒", "㇒", "㇒", "㇏"], "象", "any", None, None),
    (["厂", "5", "6", "㇒", "㇏"], "成", "any", None, None),
    (["㇒", "6", "1", "6", "㇏"], "氐", "any", None, None),
    (["𠂉", "㇏", "𠂉", "㇏"], "⺮", "head", None, None),
    (["𠂉", "2", "𠂉", "2"], "⺮", "whole", None, None),
    (["㇏", "5", "2", "㇏"], "礻", "head", None, None),
    (["2", "1", "3", "4"], "龰", "tail", None, None),
    (["彐", "6", "㇒", "㇏"], "艮", "any_mid", None, None),
    (["6", "5", "亠", "㇏"], "母", "any", None, None),
    (["二", "6", "㇒", "㇏"], "戋", "any", set("戋线钱浅残贱践栈溅笺篯饯"), None),
    (["3", "5", "5", "1"], "乌", "any", None, None),
    (["㇒", "6", "1", "6"], "氏", "any_mid", None, None),
    (["㇏", "丷", "冖"], XT, "head_mid", None, None),
    (["丷", "1", "𰀁"], "羊", "any_mid", None, None),
    (["3", "5", "㇏"], "及", "any", set("及级极吸圾汲笈岌伋芨趿靸"), None),
    (["5", "1", "5"], "弓", "head", set("弓张强费引粥弗弹弱弘弦弥疆弧弼弛犟弢鬻弭弨弶弸艴𫸩"), None),
    (["⺌", "冖"], DT, "head_mid", None, None),
    (["千", "𠆢"], "禾", "head", None, None),
    (["𰀁", "𠆢"], "末", "any", None, set("秉")),
]

def transform(sh, c):
    changed = False
    for pat, root, where, inc, exc in FAMS:
        n = len(pat)
        if inc is not None and c not in inc:
            continue
        if exc and c in exc:
            continue
        i = 0
        out = []
        while i < len(sh):
            if sh[i:i + n] == pat:
                pos = "whole" if (i == 0 and i + n == len(sh)) else ("head" if i == 0 else ("tail" if i + n == len(sh) else "mid"))
                ok = (where in ("any", "any_mid")) or \
                     (where == "head" and pos in ("head", "whole")) or \
                     (where == "whole" and pos == "whole") or \
                     (where == "tail" and pos in ("tail", "whole")) or \
                     (where == "head_mid" and pos in ("head", "whole", "mid"))
                if where == "any" and pos == "mid":
                    ok = False
                if root == "氏" and pos in ("head", "whole") and sh[i + n:i + n + 1] == ["㇏"]:
                    ok = False
                if ok:
                    out.append(root)
                    i += n
                    changed = True
                    continue
            out.append(sh[i])
            i += 1
        sh = out
    return sh, changed

def rootkeys():
    rk = json.load(open(BASE / "work/v04_rootkeys.json", encoding="utf-8"))
    mains, attach = rk["mains"], rk["attach"]
    def key_of(r, d=0):
        if r in mains:
            return mains[r]
        if r in attach and d < 4:
            return key_of(attach[r], d + 1)
        return None
    return key_of

def run_ext():
    key_of = rootkeys()
    asm = {}
    for line in open(BASE / "work/v03_assembled.tsv", encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 2 and len(p[0]) == 1 and p[0] not in asm:
            roots = [json.loads(t)["element"] for t in p[1].split(" ")]
            asm[p[0]] = [r for r in roots if not r.startswith(("szm-", "mzm-"))]
    readings = json.load(open(BASE / "work/readings.json", encoding="utf-8"))
    for fn in ["work/扩展字集_打字版.tsv", "work/扩展字集_全量.tsv"]:
        rows = [l.rstrip("\n") for l in open(BASE / fn, encoding="utf-8") if l.strip()]
        have = set(rows)
        add = []
        for l in rows:
            p = l.split("\t")
            if len(p) >= 2 and len(p[0]) == 1 and p[0] not in readings and len(p[1]) == 4:
                sh = asm.get(p[0])
                if not sh:
                    continue
                ns, ch = transform(sh, p[0])
                if not ch:
                    continue
                k1, k2 = key_of(ns[0]), key_of(ns[-1])
                if not (k1 and k2):
                    continue
                nc = p[1][:2] + k1 + k2
                nl = f"{p[0]}\t{nc}"
                if nc != p[1] and nl not in have:
                    add.append(nl)
                    have.add(nl)
        open(BASE / fn, "a", encoding="utf-8", newline="\n").write("\n".join(add) + ("\n" if add else ""))
        print(fn, "追加双码", len(add))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "ext":
        run_ext()
