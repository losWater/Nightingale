# -*- coding: utf-8 -*-
"""v0.4 A类补根批量变换：耳卜弟𠃓且专了尤韦予官腹E902 立根 + 彡挂㇒ + 戈尾重写"""
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
GF = chr(0xE902)  # E902 官字腹

BU_HEAD = set("点占战餐卢桌卓贞睿卤颅壑乩粲鸬卣")
LE_INC = set("了承函辽亟")
GE_EXC = set("辰震振晨宸娠蜃赈")

FAMS2 = [
    (["2", "5", "1", "5", "1"], GF, "any", None, None),
    (["丷", "5", "1", "5", "2", "3"], "弟", "any", None, None),
    (["5", "1", "5", "2", "3"], "弟", "any", None, None),
    (["1", "2", "2", "三"], "耳", "any", None, None),
    (["𠂇", "6", "㇏"], "尤", "any", None, None),
    (["6", "㇒", "㇏"], "戈", "any", None, GE_EXC),
    (["二", "5", "4"], "专", "any", None, None),
    (["二", "5", "2"], "韦", "any", None, None),
    (["龴", "5", "2"], "予", "any", None, None),
    (["2", "5", "三"], "且", "any", None, None),
    (["5", "3", "3"], "𠃓", "any", None, None),
    (["㇒", "㇒", "㇒"], "彡", "tail", None, None),
    (["2", "1"], "卜", "head", BU_HEAD, None),
    (["2", "4"], "卜", "tail", None, None),
    (["5", "2"], "了", "head", LE_INC, None),
]

def transform(sh, c):
    changed = False
    for pat, root, where, inc, exc in FAMS2:
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
                ok = (where == "any") or \
                     (where == "head" and pos in ("head", "whole")) or \
                     (where == "tail" and pos in ("tail", "whole"))
                if where == "any" and pos == "mid" and root in ("卜", "了"):
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

def main():
    # 1) splits.tsv + v04_final.tsv
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

    # elements_v04: 改动字重写首末
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

    # 2) yaml 加根
    for f in ["releases/v0.4/夜莺码v0.4键位布局.yaml"]:
        s = open(BASE / f, encoding="utf-8").read()
        ins = "\n".join([
            "    耳: n", "    卜: q", "    弟: x", "    𠃓: x", "    且: q",
            "    专: q", "    了: o", "    尤: t", "    韦: q", "    予: q",
            "    " + GF + ": n",
            "    彡:", "      element: ㇒",
        ])
        anchor = "    羊: z"
        assert anchor in s and "    耳: n" not in s
        s = s.replace(anchor, anchor + "\n" + ins)
        s = s.replace("description: 146根 音形方案", "description: 157根 音形方案")
        open(BASE / f, "w", encoding="utf-8", newline="\n").write(s)
    print("yaml +11主根+1附属")

    # 3) readings 新码（原位为主，多数零变化）
    rk_mains = {}
    import yaml as _y
    cfg = _y.safe_load(open(BASE / "releases/v0.4/夜莺码v0.4键位布局.yaml", encoding="utf-8"))
    attach = {}
    for k, v in cfg["form"]["mapping"].items():
        k = str(k)
        if k.startswith(("szm-", "mzm-")):
            continue
        if isinstance(v, str):
            rk_mains[k] = v
        else:
            attach[k] = str(v["element"])
    def key_of(r, d=0):
        if r in rk_mains:
            return rk_mains[r]
        if r in attach and d < 4:
            return key_of(attach[r], d + 1)
        return None
    readings = json.load(open(BASE / "work/readings.json", encoding="utf-8"))
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
    freq = {c: rs[0][0] for c, rs in readings.items()}
    n_new = 0
    gainers = []
    for c, (old, ns) in changed.items():
        if c not in readings:
            continue
        k1, k2 = key_of(ns[0]), key_of(ns[-1])
        if not (k1 and k2):
            continue
        newpairs = []
        for f, cd in readings[c]:
            if len(cd) != 4:
                continue
            nc = cd[:2] + k1 + k2
            if nc != cd and nc not in [x[1] for x in readings[c]] and nc not in [x[1] for x in newpairs]:
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
    print("新码", n_new, "条; 换主码赢家:", "".join(gainers))
    # 抽查
    for c in ["联", "我", "外", "第", "场", "官", "了", "耳", "尤", "伟", "序"]:
        if c in changed:
            print(" ", c, " ".join(changed[c][1]))

if __name__ == "__main__":
    main()
