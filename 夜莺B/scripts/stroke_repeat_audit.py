# -*- coding: utf-8 -*-
"""在低密度音节中挖掘反复出现的连续裸笔画串，辅助发现漏根。

默认排除万频字数最多的前 50 个音节，只审计其余音节涉及的万频字。
片段绝不跨越已成根部件；报告优先排列触及整字首／末端的最大重复串。
"""
import argparse
import math
from collections import defaultdict
from pathlib import Path

from b_roots import FORMAL_SPLITS, freq, name, r

STROKE = {
    "1": "横", "一": "横",
    "2": "竖", "丨": "竖",
    "3": "撇", "丿": "撇",
    "4": "点", "丶": "点",
    "5": "折", "6": "折", "乙": "折",
}


def syllable_ranking(minimum):
    chars = defaultdict(set)
    for char, readings in r.items():
        if freq.get(char, 0) < minimum:
            continue
        for _, code in readings:
            chars[code[:2]].add(char)
    return sorted(chars, key=lambda syl: (-len(chars[syl]), syl)), chars


def stroke_runs(seq):
    """返回 (起点, 终点开区间, 规范笔画元组)；根元素会截断笔画串。"""
    start = None
    labels = []
    for i, token in enumerate(seq + [None]):
        label = STROKE.get(token)
        if label is not None:
            if start is None:
                start = i
            labels.append(label)
        elif start is not None:
            yield start, i, tuple(labels)
            start, labels = None, []


def maximal_rows(occurrences, min_chars):
    rows = []
    for fragment, occs in occurrences.items():
        chars = {x[0] for x in occs}
        if len(chars) < min_chars:
            continue
        start_chars = {c for c, at_start, _ in occs if at_start}
        end_chars = {c for c, _, at_end in occs if at_end}
        visible = start_chars | end_chars
        total_freq = sum(freq.get(c, 0) for c in chars)
        # 首末可见优先，其次长度、跨字就业和频率；对超高频做对数压缩。
        score = (3 * len(visible) + len(chars)) * len(fragment) + math.log10(total_freq + 1)
        rows.append({
            "fragment": fragment, "occs": occs, "chars": chars,
            "start": start_chars, "end": end_chars, "visible": visible,
            "freq": total_freq, "score": score,
        })

    # 若更长片段覆盖完全相同的字集和首末可见集，只保留更长者。
    kept = []
    for row in sorted(rows, key=lambda x: (-len(x["fragment"]), -x["score"])):
        redundant = False
        for longer in kept:
            if (row["chars"] == longer["chars"] and row["visible"] == longer["visible"] and
                    len(row["fragment"]) < len(longer["fragment"])):
                small, big = row["fragment"], longer["fragment"]
                if any(big[i:i + len(small)] == small for i in range(len(big) - len(small) + 1)):
                    redundant = True
                    break
        if not redundant:
            kept.append(row)
    return sorted(kept, key=lambda x: (-x["score"], -len(x["visible"]), -len(x["fragment"])))


def render(rows, audited_syllables, audited_chars, limit):
    out = [
        "# 连续裸笔画重复片段审计",
        "",
        f"审计音节 {len(audited_syllables)} 个；涉及万频字 {len(audited_chars)} 个。",
        "片段不跨已成根边界；首/末表示该笔画串触及整字根序列端点。结果是候选线索，不自动立根。",
        "",
        "| 排名 | 笔画片段 | 字数 | 首端 | 末端 | 总频(万) | 示例 |",
        "|---:|---|---:|---:|---:|---:|---|",
    ]
    for i, row in enumerate(rows[:limit], 1):
        examples = sorted(row["chars"], key=lambda c: -freq.get(c, 0))[:14]
        marked = []
        for c in examples:
            flags = ("首" if c in row["start"] else "") + ("末" if c in row["end"] else "")
            marked.append(f"{c}{freq.get(c, 0)//10000}" + (f"({flags})" if flags else ""))
        out.append(
            f"| {i} | {'-'.join(row['fragment'])} | {len(row['chars'])} | "
            f"{len(row['start'])} | {len(row['end'])} | {row['freq']//10000} | {' '.join(marked)} |"
        )
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-syllables", type=int, default=50, help="排除最密集的前 N 个音节")
    ap.add_argument("--minimum", type=int, default=10000, help="单字最低总频")
    ap.add_argument("--min-len", type=int, default=2, help="最短连续裸笔画数")
    ap.add_argument("--min-chars", type=int, default=2, help="最少不同字数")
    ap.add_argument("--limit", type=int, default=80)
    ap.add_argument("--write", type=Path)
    args = ap.parse_args()

    ranking, syllable_chars = syllable_ranking(args.minimum)
    audited_syllables = set(ranking[args.top_syllables:])
    audited_chars = {
        c for syl in audited_syllables for c in syllable_chars[syl]
    }
    occurrences = defaultdict(list)
    for char in audited_chars:
        seq = FORMAL_SPLITS.get(char, [])
        for start, end, run in stroke_runs(seq):
            for length in range(args.min_len, len(run) + 1):
                for offset in range(len(run) - length + 1):
                    fragment = run[offset:offset + length]
                    occurrences[fragment].append(
                        (char, start + offset == 0, start + offset + length == len(seq))
                    )

    rows = maximal_rows(occurrences, args.min_chars)
    report = render(rows, audited_syllables, audited_chars, args.limit)
    if args.write:
        args.write.write_text(report, encoding="utf-8")
        print(f"已输出 {len(rows)} 个候选中的前 {min(args.limit, len(rows))} 个 → {args.write}")
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
