# -*- coding: utf-8 -*-
"""v0.4 B类补根批量：丂o 与n 比n 出m 直n 真b 立根 + 氺挂水o + 所左半→户w"""
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent

FAMS3 = [
    (["十", "且", "1", "八"], "真", "any", None),
    (["2", "冫", "㇒", "4"], "氺", "tail", None),
    (["十", "且", "1"], "直", "any", None),
    (["㇒", "3", "5", "1"], "户", "head", set("所")),
    (["6", "2", "山"], "出", "any", None),
    (["1", "6", "匕"], "比", "any", None),
    (["1", "5", "1"], "与", "any", None),
    (["1", "5"], "丂", "tail", None),
    (["5"], "丂", "tail", set("亏")),
]

def transform(sh, c):
    changed = False
    for pat, root, where, inc in FAMS3:
        n = len(pat)
        if inc is not None and c not in inc:
            continue
        i = 0
        out = []
        while i < len(sh):
            if sh[i:i + n] == pat:
                pos = "whole" if (i == 0 and i + n == len(sh)) else ("head" if i == 0 else ("tail" if i + n == len(sh) else "mid"))
                ok = (where == "any" and pos != "mid") or \
                     (where == "any" and pos == "mid" and root in ("真", "直", "氺")) or \
                     (where == "head" and pos in ("head", "whole")) or \
                     (where == "tail" and pos in ("tail", "whole"))
                if ok:
                    out.append(root)
                    i += n
                    changed = True
                    continue
            out.append(sh[i])
            i += 1
        sh = out
    return sh, changed

def main():
    splits = {}
    order = []
    for line in open(BASE / "work/v04_final.tsv.splits.tsv", encoding="utf-8"):
        c, _, rest = line.rstrip("\n").partition("\t")
        if c and c not in splits:
            splits[c] = rest.split(" ")
            order.append(c)
    changed = {}
    for c in order:
        if len(c) != 1:
            continue
        ns, ch = transform(splits[c], c)
        if ch:
            changed[c] = (splits[c], ns)
            splits[c] = ns
    with open(BASE / "work/v04_final.tsv.splits.tsv", "w", encoding="utf-8", newline="\n") as f:
        for c in order:
            f.write(c + "\t" + " ".join(splits[c]) + "\n")
    print("拆分变更", len(changed), "字")

    lines = []
    nfix = 0
    for line in open(BASE / "work/v04_final.tsv", encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) >= 2 and len(p[0]) == 1 and p[0] in changed:
            toks = [json.loads(t) for t in p[1].split(" ")]
            pre = [t for t in toks if t["element"].startswith(("szm-", "mzm-"))]
            toks2 = pre + [{"element": e, "index": 0} for e in changed[p[0]][1]]
            p[1] = " ".join(json.dumps(t, ensure_ascii=False, separators=(",", ":")) for t in toks2)
            nfix += 1
        lines.append("\t".join(p))
    open(BASE / "work/v04_final.tsv", "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    print("v04_final 更新", nfix)

    txt = open(BASE / "work/optimize/elements_v04.yaml", encoding="utf-8").read()
    blocks = txt.split("- 词: ")
    ne = 0
    for i, b in enumerate(blocks[1:], 1):
        w = b.split("\n", 1)[0]
        if w in changed:
            ns = changed[w][1]
            body = b.split("\n")
            keep = []
            for j, l in enumerate(body):
                st = l.strip()
                if st.startswith("- element: szm-") or st.startswith("- element: mzm-"):
                    keep.append(l)
                    keep.append(body[j + 1])
            freqline = [l for l in body if l.strip().startswith("频率:")]
            nb = [w, "  元素序列:"] + keep
            for e in (ns[0], ns[-1]):
                nb.append("  - element: " + e)
                nb.append("    index: 0")
            nb += freqline
            blocks[i] = "\n".join(nb) + "\n"
            ne += 1
    open(BASE / "work/optimize/elements_v04.yaml", "w", encoding="utf-8", newline="\n").write("- 词: ".join(blocks))
    print("elements 更新", ne)

    f = "releases/v0.4/夜莺码v0.4键位布局.yaml"
    s = open(BASE / f, encoding="utf-8").read()
    ins = "\n".join([
        "    丂: o", "    与: n", "    比: n", "    出: m", "    直: n", "    真: b",
        "    氺:", "      element: 水",
    ])
    anchor = "    羊: z"
    assert anchor in s and "    丂: o" not in s
    s = s.replace(anchor, anchor + "\n" + ins)
    s = s.replace("description: 157根 音形方案", "description: 163根 音形方案")
    open(BASE / f, "w", encoding="utf-8", newline="\n").write(s)
    print("yaml +6主根+1附属")
    for c in ["号", "亏", "考", "比", "出", "值", "真", "康", "所", "与", "屈", "镇"]:
        if c in changed:
            print(" ", c, " ".join(changed[c][1]))

if __name__ == "__main__":
    main()
