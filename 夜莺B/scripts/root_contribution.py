# -*- coding: utf-8 -*-
"""统计当前根集在单字音形码中的首末覆盖与频率贡献。"""
import json
from collections import defaultdict

from b_roots import B, FORMAL_SPLITS, HOST, freq, name


def root(item):
    if item in HOST:
        return str(HOST[item])
    if item in ("1", "一"):
        return "横"
    if item in ("2", "丨"):
        return "竖"
    if item in ("3", "丿"):
        return "撇"
    if item in ("4", "丶", "㇏"):
        return "点"
    if item in ("5", "6", "乙"):
        return "折"
    return name(item)


def main():
    readings = json.load(open(B + "work/readings.json", encoding="utf-8"))
    stats = defaultdict(lambda: {"chars": set(), "head_chars": set(), "tail_chars": set(),
                                 "head_freq": 0, "tail_freq": 0, "strokes": 0})
    total = 0
    for char, seq in FORMAL_SPLITS.items():
        if not seq or char not in readings:
            continue
        weight = freq[char]
        head, tail = root(seq[0]), root(seq[-1])
        total += weight * 2
        for position, value in (("head", head), ("tail", tail)):
            s = stats[value]
            s["chars"].add(char)
            s[position + "_chars"].add(char)
            s[position + "_freq"] += weight
            s["strokes"] += weight

    rows = sorted(stats.items(), key=lambda kv: -kv[1]["strokes"])
    out = [
        "# 字根贡献量（单字首末形码）", "",
        "按当前正式拆分统计；中间根不可见，不计入。频率贡献按每字首、末各一次击键累计；同根首末相同则计两次。", "",
        "| 排名 | 根 | 覆盖字数 | 首根字数 | 末根字数 | 首频(万) | 末频(万) | 总贡献(万) | 占全部形码 |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, (r, s) in enumerate(rows, 1):
        share = s["strokes"] / total * 100 if total else 0
        out.append(f"| {i} | {r} | {len(s['chars'])} | {len(s['head_chars'])} | {len(s['tail_chars'])} | "
                   f"{s['head_freq']//10000} | {s['tail_freq']//10000} | {s['strokes']//10000} | {share:.2f}% |")
    path = B + "夜莺B/work/字根贡献量.md"
    open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
    print("\n".join(out[:43]))
    print(path)


if __name__ == "__main__":
    main()
