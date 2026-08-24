# -*- coding: utf-8 -*-
"""输出当前方案的全局三码、全码重码审计，并按整字汇总多音字问题。"""
import json
import sys
from collections import defaultdict

from candidate_root_check import WORK, forms, full_pairs, load_host, parse_splits, short_state

BASE = WORK.parent.parent


def main():
    minimum = int(float(sys.argv[1]) * 10000) if len(sys.argv) > 1 else 10000
    readings = json.loads((BASE / "work/readings.json").read_text(encoding="utf-8"))
    freq = {char: rows[0][0] for char, rows in readings.items()}
    reading_freq = {(char, code[:2]): value for char, rows in readings.items() for value, code in rows}
    form = forms(parse_splits(WORK / "analysis.tsv.splits.tsv", load_host()), readings)
    losers, piles = short_state(form, freq, minimum, reading_freq)
    pairs = full_pairs(form)

    short_by_char = defaultdict(set)
    for char, syl in losers:
        short_by_char[char].add(syl)
    full_by_char = defaultdict(set)
    for syl, left, right in pairs:
        full_by_char[left].add((syl, right))
        full_by_char[right].add((syl, left))

    out = [
        "# 夜莺B 全局三码／全码审计",
        "",
        f"三码统计仅纳入字频 ≥ {minimum // 10000} 万的字；二简按每音节最高频字排除，每个 `音节+首根` 仅保留一个三码位。",
        "全码覆盖全部字音。多音字按整字汇总：任一读音有问题，该字就保留在表中，不允许用另一个安全读音抵消。",
        "",
        f"- 三码落选字音：{len(losers)}；涉及整字：{len(short_by_char)}",
        f"- 全码重码字对：{len(pairs)}；涉及整字：{len(full_by_char)}",
        "",
        "## 三码高频落选",
        "",
        "| 字 | 频(万) | 落选读音 | 首末根 | 同堆竞争者 |",
        "|---|---:|---|---|---|",
    ]
    for char in sorted(short_by_char, key=lambda c: -freq[c]):
        syls = sorted(short_by_char[char])
        details = []
        roots = []
        for syl in syls:
            head, tail = form[(char, syl)]
            roots.append(f"{syl}:{head}—{tail}")
            pile = sorted(piles[(syl, head)], key=lambda c: -freq[c])
            details.append(f"{syl}:" + "/".join(f"{c}{freq[c]//10000}" for c in pile[:8]))
        out.append(f"| {char} | {freq[char]//10000} | {'、'.join(syls)} | {'；'.join(roots)} | {'；'.join(details)} |")

    out += ["", "## 全码高频重码", "", "| 字 | 频(万) | 出问题读音与同码字 |", "|---|---:|---|"]
    for char in sorted(full_by_char, key=lambda c: -freq[c]):
        items = sorted(full_by_char[char], key=lambda x: (-freq[x[1]], x))
        text = "；".join(f"{syl}:{other}{freq[other]//10000}" for syl, other in items[:16])
        out.append(f"| {char} | {freq[char]//10000} | {text} |")

    path = WORK / "全局三码全码审计.md"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"三码落选 {len(losers)} 字音/{len(short_by_char)} 字；全码重码 {len(pairs)} 对/{len(full_by_char)} 字")
    print(path)


if __name__ == "__main__":
    main()
