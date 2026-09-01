#!/usr/bin/env python3
"""审计 SUBTLEX-CH 词频能否构造按读音字频候选；不改写权威字音表。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


TONE_RE = re.compile(r"[1-5]$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def toneless(syllable: str) -> str:
    value = TONE_RE.sub("", syllable.strip().lower())
    return value.replace("u:", "v").replace("ü", "v")


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--zip", dest="zip_path", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    pairs, readings_by_char = load_candidates(args.candidates)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    reason_counts: Counter[str] = Counter()
    row_counts: Counter[str] = Counter()
    token_counts: Counter[str] = Counter()
    pair_counts: Counter[tuple[str, str]] = Counter()
    tone_details: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    evidence_types: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    exceptions: list[dict[str, object]] = []
    total_word_frequency = 0
    accepted_word_frequency = 0

    with args.source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"Word", "Length", "Pinyin", "WCount"}
        if not required.issubset(reader.fieldnames or []):
            raise SystemExit(f"SUBTLEX 列缺失：{sorted(required - set(reader.fieldnames or []))}")

        for line_no, row in enumerate(reader, 2):
            row_counts["all"] += 1
            word = row["Word"]
            pinyin = row["Pinyin"].strip()
            try:
                frequency = int(row["WCount"])
            except ValueError:
                reason = "频率非整数"
                frequency = 0
                reason_counts[reason] += 1
                exceptions.append({"行号": line_no, "词": word, "拼音": pinyin, "频率": row["WCount"], "原因": reason})
                continue
            total_word_frequency += frequency
            syllables = pinyin.split()
            reasons: list[str] = []
            if len(word) != len(syllables):
                reasons.append("字数与音节数不等")
            normalized_syllables = [normalized_options(item) for item in syllables]
            if any(len(options) != 1 for options in normalized_syllables):
                reasons.append("去调后音节仍含多个候选读音")
            if not reasons:
                for char, options in zip(word, normalized_syllables):
                    reading = next(iter(options))
                    if char not in readings_by_char:
                        reasons.append("字不在当前8105")
                        break
                    if reading not in readings_by_char[char]:
                        reasons.append("读音不在当前8454候选")
                        break
            if reasons:
                for reason in sorted(set(reasons)):
                    reason_counts[reason] += 1
                exceptions.append({
                    "行号": line_no,
                    "词": word,
                    "拼音": pinyin,
                    "频率": frequency,
                    "原因": "；".join(sorted(set(reasons))),
                })
                continue

            row_counts["accepted"] += 1
            accepted_word_frequency += frequency
            evidence_type = "单字唯一读音" if len(word) == 1 else "多字词逐音节对齐"
            for char, syllable, options in zip(word, syllables, normalized_syllables):
                reading = next(iter(options))
                pair = (char, reading)
                pair_counts[pair] += frequency
                tone_details[pair][syllable] += frequency
                evidence_types[pair][evidence_type] += frequency
                token_counts["accepted_character_tokens"] += frequency

    candidate_path = args.output_dir / "SUBTLEX分读音频率候选.tsv"
    with candidate_path.open("w", encoding="utf-8-sig", newline="") as handle:
        fieldnames = ["汉字", "拼音", "候选频率", "带调证据", "证据类型", "当前候选是否命中", "状态"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for char, reading in sorted(pairs, key=lambda item: (-pair_counts[item], item[0], item[1])):
            pair = (char, reading)
            tones = ";".join(f"{key}:{value}" for key, value in tone_details[pair].most_common())
            evidence = ";".join(f"{key}:{value}" for key, value in evidence_types[pair].most_common())
            writer.writerow({
                "汉字": char,
                "拼音": reading,
                "候选频率": pair_counts[pair],
                "带调证据": tones,
                "证据类型": evidence,
                "当前候选是否命中": "是",
                "状态": "候选；未覆盖频次不得视为0" if pair_counts[pair] == 0 else "候选；待人工验收",
            })

    exception_path = args.output_dir / "SUBTLEX字音异常.tsv"
    with exception_path.open("w", encoding="utf-8-sig", newline="") as handle:
        fieldnames = ["行号", "词", "拼音", "频率", "原因"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(exceptions)

    report = {
        "generated_at": datetime.now(ZoneInfo("Australia/Sydney")).isoformat(timespec="seconds"),
        "source": str(args.source.resolve()),
        "source_sha256": sha256(args.source),
        "source_zip": str(args.zip_path.resolve()),
        "source_zip_sha256": sha256(args.zip_path),
        "candidate_source": str(args.candidates.resolve()),
        "candidate_source_sha256": sha256(args.candidates),
        "rows_total": row_counts["all"],
        "rows_accepted": row_counts["accepted"],
        "rows_rejected": row_counts["all"] - row_counts["accepted"],
        "word_frequency_total": total_word_frequency,
        "word_frequency_accepted": accepted_word_frequency,
        "word_frequency_accepted_ratio": accepted_word_frequency / total_word_frequency if total_word_frequency else 0,
        "accepted_character_tokens": token_counts["accepted_character_tokens"],
        "current_reading_candidates": len(pairs),
        "candidates_with_evidence": sum(value > 0 for value in pair_counts.values()),
        "candidates_without_evidence": sum(pair_counts[pair] == 0 for pair in pairs),
        "rejection_reasons_by_row": dict(reason_counts),
        "important_examples": {
            char: {reading: pair_counts[(char, reading)] for reading in sorted(readings_by_char.get(char, []))}
            for char in "行重长都得地着还咯哼谁的了好"
        },
        "interpretation_limit": "仅计入拼音唯一且逐字对齐的词条。被拒绝词条中的频次尚未分配，因此候选频率是有证据下界，不是最终真值。",
    }
    json_path = args.output_dir / "SUBTLEX字音来源审计.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_path = args.output_dir / "SUBTLEX字音来源审计.md"
    lines = [
        "# SUBTLEX-CH 按读音字频来源审计",
        "",
        f"- 总词条：{report['rows_total']:,}",
        f"- 可逐字唯一对齐词条：{report['rows_accepted']:,}",
        f"- 拒绝词条：{report['rows_rejected']:,}",
        f"- 总词频：{report['word_frequency_total']:,}",
        f"- 可唯一分配词频：{report['word_frequency_accepted']:,}（{report['word_frequency_accepted_ratio']:.2%}）",
        f"- 当前 8454 字音项有证据：{report['candidates_with_evidence']:,}",
        f"- 当前 8454 字音项暂无证据：{report['candidates_without_evidence']:,}",
        "",
        "## 解释限制",
        "",
        report["interpretation_limit"],
        "",
        "## 拒绝原因（按词条计）",
        "",
    ]
    lines.extend(f"- {key}：{value:,}" for key, value in reason_counts.most_common())
    lines.extend(["", "## 重点多音字候选频率", ""])
    for char, values in report["important_examples"].items():
        lines.append(f"- {char}：" + "，".join(f"{reading}={value:,}" for reading, value in values.items()))
    lines.extend(["", "本报告和候选表均不改写当前权威字音表，也不触发退火。", ""])
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
