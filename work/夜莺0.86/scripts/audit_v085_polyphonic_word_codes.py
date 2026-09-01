#!/usr/bin/env python3
"""用简单鹤整词码对照夜莺合法单字音码，筛查 0.8.5 多音词误码候选。"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path


def read_nightingale(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        parts = raw.split("\t")
        if len(parts) != 2:
            raise ValueError(f"{path}:{line_number}: 非法码表行")
        rows.append((parts[0], parts[1]))
    return rows


def read_reference(path: Path) -> dict[str, list[tuple[int, str]]]:
    by_word: dict[str, list[tuple[int, str]]] = defaultdict(list)
    # 参考挂接表是 Windows Unicode，即 UTF-16 LE BOM。
    for line_number, raw in enumerate(path.read_text(encoding="utf-16").splitlines(), 1):
        left, comma, word = raw.partition(",")
        code, equal, rank = left.partition("=")
        if not comma or not equal or not rank.isdigit():
            raise ValueError(f"{path}:{line_number}: 非法参考行")
        by_word[word].append((int(rank), code))
    return by_word


def encode_word(word: str, sounds: tuple[str, ...]) -> str:
    if len(word) == 2:
        return sounds[0] + sounds[1]
    if len(word) == 3:
        return sounds[0][0] + sounds[1][0] + sounds[2]
    selected = sounds[:3] + sounds[-1:]
    return "".join(code[0] for code in selected)


def legal_codes(word: str, sounds_by_char: dict[str, set[str]]) -> set[str]:
    if len(word) < 2 or any(char not in sounds_by_char for char in word):
        return set()
    return {encode_word(word, values) for values in product(*(sorted(sounds_by_char[c]) for c in word))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", type=Path, required=True)
    parser.add_argument("--combined", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    single = read_nightingale(args.single)
    combined = read_nightingale(args.combined)
    reference = read_reference(args.reference)
    sounds_by_char: dict[str, set[str]] = defaultdict(set)
    for char, code in single:
        if len(char) == 1 and len(code) == 4:
            sounds_by_char[char].add(code[:2])

    findings: list[dict[str, object]] = []
    compared = 0
    for word, current_code in combined:
        if len(word) < 2 or word not in reference:
            continue
        legal = legal_codes(word, sounds_by_char)
        applicable = sorted(
            {(rank, code) for rank, code in reference[word] if len(code) == 4 and code in legal}
        )
        if not applicable:
            continue
        compared += 1
        applicable_codes = {code for _, code in applicable}
        if current_code in applicable_codes:
            continue
        recommended = applicable[0][1]
        findings.append({
            "词": word,
            "词长": len(word),
            "当前码": current_code,
            "参考建议码": recommended,
            "参考合法码全集": " ".join(code for _, code in applicable),
            "当前码是否合法组合": "是" if current_code in legal else "否",
            "涉及多音字": " ".join(
                f"{char}:{'/'.join(sorted(sounds_by_char[char]))}"
                for char in word
                if len(sounds_by_char[char]) > 1
            ),
            "状态": "待人工复核；不自动改码",
        })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    tsv = args.output_dir / "多音词词码差异候选.tsv"
    fields = ["词", "词长", "当前码", "参考建议码", "参考合法码全集", "当前码是否合法组合", "涉及多音字", "状态"]
    with tsv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(findings)

    by_length = Counter(int(row["词长"]) if int(row["词长"]) < 4 else 4 for row in findings)
    changed_chars: Counter[str] = Counter()
    for row in findings:
        for item in str(row["涉及多音字"]).split():
            changed_chars[item.split(":", 1)[0]] += 1
    examples = findings[:30]
    lines = [
        "# 夜莺 0.8.5 多音词词码排查",
        "",
        f"- 夜莺与参考表同词、且参考四码可由夜莺合法单字音码组成：{compared:,} 条；",
        f"- 当前码与参考合法词码不一致：{len(findings):,} 条；",
        f"- 二字词：{by_length[2]:,}；三字词：{by_length[3]:,}；四字及以上：{by_length[4]:,}；",
        "- 这些是高价值复核候选，不等同于已确认错误；简单鹤参考表不是夜莺权威读音源。",
        "",
        "## 高频出现的多音字（按候选条数）",
        "",
        ", ".join(f"{char} {count}" for char, count in changed_chars.most_common(30)),
        "",
        "## 前 30 条候选",
        "",
        "| 词 | 当前码 | 参考建议码 | 涉及多音字 |",
        "|---|---|---|---|",
    ]
    lines.extend(
        f"| {row['词']} | {row['当前码']} | {row['参考建议码']} | {row['涉及多音字']} |"
        for row in examples
    )
    lines.extend([
        "",
        "完整明细见 `多音词词码差异候选.tsv`。建议先复核常用二字词，再分批登记纠错；不要整表自动覆盖。",
        "",
    ])
    (args.output_dir / "结果摘要.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"compared={compared} findings={len(findings)} lengths={dict(sorted(by_length.items()))}")


if __name__ == "__main__":
    main()
