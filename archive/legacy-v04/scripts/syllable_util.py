# -*- coding: utf-8 -*-
"""音节简码利用率：每音节 27 位（1 二简 + 26 三简），多音字各读音计入，字频用总频。
覆盖 = 字有任何 ≤3 键简码（含一简、副读音简码）。
得分 = 该音节已覆盖字的频率和 / 理想前k字频率和（k=min(27,字数)）。
用法: python scripts/syllable_util.py [纯单版路径] [readings路径]"""
import io, sys, json
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
pure = sys.argv[1] if len(sys.argv) > 1 else "D:/nightingale/releases/v0.4/夜莺码v0.4纯单版.txt"
rd = sys.argv[2] if len(sys.argv) > 2 else "D:/nightingale/work/readings.json"
r = json.load(open(rd, encoding="utf-8"))
freq = {c: v[0][0] for c, v in r.items()}
syl = defaultdict(set)
for c, rs in r.items():
    for f, cd in rs:
        syl[cd[:2]].add(c)
short = defaultdict(set)   # 音节 -> {(字, 简码)}  仅二/三简，统计位占用
anyshort = defaultdict(set)
for l in open(pure, encoding="utf-8"):
    c, _, cd = l.strip().partition("\t")
    if len(cd) <= 3 and c in freq:
        anyshort[c].add(cd)
        if len(cd) >= 2:
            short[cd[:2]].add((c, cd))
rows = []
for s, chars in syl.items():
    chars = sorted(chars, key=lambda c: -freq[c])
    n = len(chars); k = min(27, n)
    used = {cd for c, cd in short[s]}
    covered = {c for c in chars if anyshort.get(c)}
    ideal = sum(freq[c] for c in chars[:k]) or 1
    got = sum(freq[c] for c in chars[:k] if c in covered)
    miss = [c for c in chars[:k] if c not in covered]
    rows.append(dict(s=s, n=n, used=len(used), free=27 - len(used), score=got / ideal,
                     tot=sum(freq[c] for c in chars), miss=miss))
rows.sort(key=lambda x: -x["n"])
with open("D:/nightingale/work/音节简码利用率.tsv", "w", encoding="utf-8") as f:
    f.write("音节\t字数\t已用位\t空位\t得分\t音节总频\t理想前k未获简码字\n")
    for x in rows:
        f.write(f"{x['s']}\t{x['n']}\t{x['used']}\t{x['free']}\t{x['score']*100:.1f}\t{x['tot']}\t"
                + " ".join(c + str(freq[c] // 10000) for c in x["miss"]) + "\n")
print(f"音节数 {len(rows)}；总简码位 {27*len(rows)}；已用 {sum(x['used'] for x in rows)}；总体覆盖率 {sum(x['used'] for x in rows)/(27*len(rows))*100:.1f}%")
w = sum(x["tot"] for x in rows)
print(f"频率加权分配得分 {sum(x['score']*x['tot'] for x in rows)/w*100:.2f}%")
full = [x for x in rows if x["n"] >= 27]
print(f"满员音节(字数≥27) {len(full)} 个：平均已用 {sum(x['used'] for x in full)/len(full):.1f}/27，平均得分 {sum(x['score'] for x in full)/len(full)*100:.1f}%")
act = sorted([x for x in rows if x["free"] > 0 and x["miss"]], key=lambda x: -sum(freq[c] for c in x["miss"]))
print("\n== 可行动：有空位且理想前k里还有字没简码（按漏掉频率排）==")
print("音节  字数 已用 空位  得分   漏掉字(频万)")
for x in act[:40]:
    print(f"{x['s']:4s} {x['n']:4d}  {x['used']:2d}  {x['free']:2d}  {x['score']*100:6.1f}%  {' '.join(c+str(freq[c]//10000) for c in x['miss'][:10])}")
print("\n== 得分最低的满员音节 ==")
for x in sorted(full, key=lambda x: x["score"])[:15]:
    print(f"{x['s']:4s} {x['n']:4d}  {x['used']:2d}  {x['free']:2d}  {x['score']*100:6.1f}%  {' '.join(c+str(freq[c]//10000) for c in x['miss'][:10])}")
print("\n全表: work/音节简码利用率.tsv")
