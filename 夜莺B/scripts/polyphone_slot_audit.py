# -*- coding: utf-8 -*-
"""检查多音字是否借主读音总频，抢占冷门读音下的二简／三码位。"""
import json
from collections import defaultdict

from candidate_root_check import RULES, WORK, forms, load_host, parse_splits

BASE = WORK.parent.parent


def main():
    readings = json.loads((BASE / "work/readings.json").read_text(encoding="utf-8"))
    total = {c: rows[0][0] for c, rows in readings.items()}
    reading_freq = {}
    primary = {}
    for char, rows in readings.items():
        primary[char] = rows[0][1][:2]
        for value, code in rows:
            key = (char, code[:2])
            reading_freq[key] = max(value, reading_freq.get(key, -1))

    form = forms(parse_splits(WORK / "analysis.tsv.splits.tsv", load_host()), readings)
    syllables = defaultdict(set)
    for char, syl in form:
        syllables[syl].add(char)

    old_two = {}
    true_two = {}
    for syl, chars in syllables.items():
        old_two[syl] = max(chars, key=lambda c: (total[c], c))
        true_two[syl] = max(chars, key=lambda c: (reading_freq[(c, syl)], total[c], c))
    for syl, char in RULES.get("two_code_overrides", {}).items():
        if char in syllables.get(syl, set()):
            true_two[syl] = char

    old_piles = defaultdict(set)
    true_piles = defaultdict(set)
    for (char, syl), (head, _) in form.items():
        if total[char] >= 10000 and char != old_two[syl]:
            old_piles[(syl, head)].add(char)
        if reading_freq[(char, syl)] >= 10000 and char != true_two[syl]:
            true_piles[(syl, head)].add(char)

    def winner(syl, head, chars, corrected):
        preferred = RULES.get("short_code_overrides", {}).get(str(syl), {}).get(str(head))
        if preferred in chars:
            return preferred
        score = reading_freq if corrected else {(c, syl): total[c] for c in chars}
        return max(chars, key=lambda c: (score[(c, syl)], total[c], c)) if chars else None

    rows = []
    for key in sorted(set(old_piles) | set(true_piles)):
        syl, head = key
        old = winner(syl, head, old_piles[key], False)
        new = winner(syl, head, true_piles[key], True)
        if old != new:
            rows.append((syl, head, old, new))

    out = [
        "# 多音字偷占简码位审计", "",
        "旧口径使用整字主频；校正口径使用该字在当前读音下的读音频率。人工简码覆盖优先于两种排序。", "",
        "## 二简位变化", "", "| 音节 | 旧占位 | 当前读音频 | 主读音 | 应占位 | 当前读音频 |", "|---|---|---:|---|---|---:|",
    ]
    two_changes = []
    for syl in sorted(syllables):
        old, new = old_two[syl], true_two[syl]
        if old != new:
            two_changes.append((syl, old, new))
            out.append(f"| {syl} | {old} | {reading_freq[(old,syl)]//10000} | {primary[old]} | {new} | {reading_freq[(new,syl)]//10000} |")

    out += ["", "## 三码位变化", "", "| 音节 | 首根 | 旧占位 | 当前读音频 | 主读音 | 应占位 | 当前读音频 |", "|---|---|---|---:|---|---|---:|"]
    for syl, head, old, new in rows:
        old_text = old or "—"
        new_text = new or "—"
        old_freq = reading_freq[(old, syl)] // 10000 if old else 0
        new_freq = reading_freq[(new, syl)] // 10000 if new else 0
        old_primary = primary[old] if old else "—"
        out.append(f"| {syl} | {head} | {old_text} | {old_freq} | {old_primary} | {new_text} | {new_freq} |")

    path = WORK / "多音字偷占简码位审计.md"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"二简变化 {len(two_changes)}；三码变化 {len(rows)}")
    print(path)


if __name__ == "__main__":
    main()
