#!/usr/bin/env python3
"""用完整 Chai 词条唯一读音消解 SUBTLEX 多字词；输出候选，不改权威表。"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


TONE_RE = re.compile(r"[1-5]$")


def toneless(value: str) -> str:
    return TONE_RE.sub("", value.strip().lower()).replace("u:", "v").replace("ü", "v")


def normalized_options(syllable: str) -> set[str]:
    return {toneless(item) for item in syllable.split("/") if item.strip()}


def load_candidates(path: Path) -> tuple[set[tuple[str, str]], dict[str, set[str]]]:
    pairs: set[tuple[str, str]] = set()
    by_char: dict[str, set[str]] = defaultdict(set)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            pair = (row["汉字"], row["拼音"])
            pairs.add(pair)
            by_char[pair[0]].add(pair[1])
    return pairs, by_char


def load_chai(path: Path) -> dict[str, set[tuple[str, ...]]]:
    result: dict[str, set[tuple[str, ...]]] = defaultdict(set)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for line in handle:
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) < 2 or not fields[1].strip():
                continue
            result[fields[0]].add(tuple(fields[1].strip().split()))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subtlex", type=Path, required=True)
    parser.add_argument("--chai", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    pairs, by_char = load_candidates(args.candidates)
    chai = load_chai(args.chai)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    direct: Counter[tuple[str, str]] = Counter()
    resolved: Counter[tuple[str, str]] = Counter()
    tone_evidence: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    unresolved: list[dict[str, object]] = []
    stats: Counter[str] = Counter()

    with args.subtlex.open("r", encoding="utf-8-sig", newline="") as handle:
        for line_no, row in enumerate(csv.DictReader(handle, delimiter="\t"), 2):
            word = row["Word"]
            source_pinyin = row["Pinyin"].strip()
            frequency = int(row["WCount"])
            source_syllables = tuple(source_pinyin.split())
            source_options = tuple(normalized_options(syllable) for syllable in source_syllables)
            has_alternatives = any(len(options) != 1 for options in source_options)

            if len(word) == len(source_syllables) and not has_alternatives:
                normalized = tuple(next(iter(options)) for options in source_options)
                if all(char in by_char and reading in by_char[char] for char, reading in zip(word, normalized)):
                    stats["direct_rows"] += 1
                    stats["direct_word_frequency"] += frequency
                    for char, reading, tone in zip(word, normalized, source_syllables):
                        direct[(char, reading)] += frequency
                        tone_evidence[(char, reading)][tone] += frequency
                    continue

            if len(word) <= 1 or not has_alternatives:
                continue

            stats["ambiguous_multiword_rows"] += 1
            stats["ambiguous_multiword_frequency"] += frequency
            readings = chai.get(word, set())
            reasons: list[str] = []
            if not readings:
                reasons.append("Chai无完整词条")
            elif len(readings) != 1:
                reasons.append("Chai完整词条读音不唯一")
            else:
                selected = next(iter(readings))
                if len(selected) != len(word):
                    reasons.append("Chai音节数与字数不等")
                else:
                    normalized = tuple(toneless(item) for item in selected)
                    if not all(char in by_char and reading in by_char[char] for char, reading in zip(word, normalized)):
                        reasons.append("Chai读音不在当前8454候选")

            if reasons:
                stats["unresolved_rows"] += 1
                stats["unresolved_word_frequency"] += frequency
                unresolved.append({
                    "行号": line_no,
                    "词": word,
                    "SUBTLEX拼音": source_pinyin,
                    "词频": frequency,
                    "Chai读音": " | ".join(" ".join(item) for item in sorted(readings)),
                    "原因": "；".join(reasons),
                })
                continue

            stats["resolved_rows"] += 1
            stats["resolved_word_frequency"] += frequency
            selected = next(iter(readings))
            for char, tone in zip(word, selected):
                reading = toneless(tone)
                resolved[(char, reading)] += frequency
                tone_evidence[(char, reading)][tone] += frequency

    output = args.output_dir / "SUBTLEX整词消歧后分读音频率候选.tsv"
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["汉字", "拼音", "直接唯一频率", "Chai整词消歧频率", "合计候选频率", "带调证据", "状态"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for pair in sorted(pairs, key=lambda item: (-(direct[item] + resolved[item]), item[0], item[1])):
            writer.writerow({
                "汉字": pair[0],
                "拼音": pair[1],
                "直接唯一频率": direct[pair],
                "Chai整词消歧频率": resolved[pair],
                "合计候选频率": direct[pair] + resolved[pair],
                "带调证据": ";".join(f"{key}:{value}" for key, value in tone_evidence[pair].most_common()),
                "状态": "候选；未分配剩余量不得视为0",
            })

    unresolved_path = args.output_dir / "SUBTLEX整词消歧未解决.tsv"
    with unresolved_path.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["行号", "词", "SUBTLEX拼音", "词频", "Chai读音", "原因"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(unresolved)

    total = stats["direct_word_frequency"] + stats["ambiguous_multiword_frequency"]
    report = {
        **stats,
        "ambiguous_multiword_resolution_ratio_by_rows": stats["resolved_rows"] / stats["ambiguous_multiword_rows"] if stats["ambiguous_multiword_rows"] else 0,
        "ambiguous_multiword_resolution_ratio_by_frequency": stats["resolved_word_frequency"] / stats["ambiguous_multiword_frequency"] if stats["ambiguous_multiword_frequency"] else 0,
        "direct_plus_resolved_word_frequency": stats["direct_word_frequency"] + stats["resolved_word_frequency"],
        "scope_frequency_denominator": total,
        "important_examples": {},
        "status": "候选；未处理单字多音词，未覆盖频率不得视为0",
    }
    for word in ["银行", "行动", "行为", "长大", "长度", "重要", "重新", "还有", "归还", "首都"]:
        report["important_examples"][word] = [" ".join(item) for item in sorted(chai.get(word, set()))]

    (args.output_dir / "SUBTLEX整词消歧审计.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# SUBTLEX 多字词完整词条消歧审计",
        "",
        f"- 原本直接唯一词条：{stats['direct_rows']:,}，词频 {stats['direct_word_frequency']:,}",
        f"- 待消歧多字词：{stats['ambiguous_multiword_rows']:,}，词频 {stats['ambiguous_multiword_frequency']:,}",
        f"- Chai 完整词条唯一解决：{stats['resolved_rows']:,}，词频 {stats['resolved_word_frequency']:,}",
        f"- 未解决：{stats['unresolved_rows']:,}，词频 {stats['unresolved_word_frequency']:,}",
        f"- 多字歧义词按词频解决率：{report['ambiguous_multiword_resolution_ratio_by_frequency']:.2%}",
        f"- 直接唯一＋整词消歧词频：{report['direct_plus_resolved_word_frequency']:,}",
        "",
        "单字多音词完全未参与本轮。所有结果仍是候选，不改写当前权威字音表。",
        "",
    ]
    (args.output_dir / "SUBTLEX整词消歧审计.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
