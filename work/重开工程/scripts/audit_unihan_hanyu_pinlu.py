#!/usr/bin/env python3
"""提取并审计 Unicode Unihan kHanyuPinlu 分读音频率。"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


ENTRY_RE = re.compile(r"([^\s(]+)\((\d+)\)")
TONE_DIGIT_RE = re.compile(r"[1-5]$")


def toneless(value: str) -> str:
    value = TONE_DIGIT_RE.sub("", value.strip().lower()).replace("u:", "ü")
    decomposed = unicodedata.normalize("NFD", value)
    output: list[str] = []
    index = 0
    while index < len(decomposed):
        char = decomposed[index]
        if unicodedata.combining(char):
            index += 1
            continue
        marks: list[str] = []
        cursor = index + 1
        while cursor < len(decomposed) and unicodedata.combining(decomposed[cursor]):
            marks.append(decomposed[cursor])
            cursor += 1
        output.append("v" if char == "u" and "\u0308" in marks else char)
        index = cursor
    return "".join(output)


def load_current(path: Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            result[row["汉字"]].add(row["拼音"])
    return result


def load_chai_single(path: Path) -> dict[str, Counter[str]]:
    result: dict[str, Counter[str]] = defaultdict(Counter)
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) < 3 or len(fields[0]) != 1 or " " in fields[1] or not fields[1]:
                continue
            try:
                frequency = int(fields[2])
            except ValueError:
                continue
            result[fields[0]][toneless(fields[1])] += frequency
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unihan", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--priority", type=Path, required=True)
    parser.add_argument("--chai", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    current = load_current(args.current)
    chai = load_chai_single(args.chai)
    raw: dict[str, list[tuple[str, int]]] = {}
    with args.unihan.open("r", encoding="utf-8") as handle:
        for line in handle:
            if "\tkHanyuPinlu\t" not in line:
                continue
            codepoint, _, value = line.rstrip("\n").split("\t", 2)
            char = chr(int(codepoint[2:], 16))
            entries = [(reading, int(frequency)) for reading, frequency in ENTRY_RE.findall(value)]
            if not entries:
                raise SystemExit(f"无法解析 {codepoint}: {value}")
            raw[char] = entries

    merged: dict[str, Counter[str]] = {}
    tone_details: dict[tuple[str, str], list[tuple[str, int]]] = defaultdict(list)
    for char, entries in raw.items():
        counts: Counter[str] = Counter()
        for reading, frequency in entries:
            normalized = toneless(reading)
            counts[normalized] += frequency
            tone_details[(char, normalized)].append((reading, frequency))
        if sum(counts.values()) != sum(frequency for _, frequency in entries):
            raise SystemExit(f"频率不守恒：{char}")
        merged[char] = counts

    output = args.output_dir / "Unihan分读音频率.tsv"
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["汉字", "拼音", "频率", "字内占比", "带调来源明细", "当前8454状态"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for char in sorted(merged):
            total = sum(merged[char].values())
            for reading, frequency in merged[char].most_common():
                if char not in current:
                    status = "字不在当前8105"
                elif reading not in current[char]:
                    status = "读音不在当前8454"
                else:
                    status = "命中"
                writer.writerow({
                    "汉字": char,
                    "拼音": reading,
                    "频率": frequency,
                    "字内占比": f"{frequency / total:.8%}",
                    "带调来源明细": ";".join(f"{tone}:{count}" for tone, count in tone_details[(char, reading)]),
                    "当前8454状态": status,
                })

    priority_rows: list[dict[str, str]] = []
    with args.priority.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            char = row["汉字"]
            counts = merged.get(char, Counter())
            chai_counts = chai.get(char, Counter())
            total = sum(counts.values())
            priority_rows.append({
                **row,
                "Unihan去调频率": ";".join(f"{key}:{value}" for key, value in counts.most_common()),
                "Unihan比例": ";".join(f"{key}:{value / total:.4%}" for key, value in counts.most_common()) if total else "",
                "Chai去调频率": ";".join(f"{key}:{value}" for key, value in chai_counts.most_common()),
                "Unihan覆盖状态": "覆盖" if counts else "未覆盖",
                "读音集合关系": (
                    "一致" if counts and set(counts) == current.get(char, set())
                    else "Unihan为当前子集" if counts and set(counts) < current.get(char, set())
                    else "存在差异" if counts else "无法比较"
                ),
            })

    audit_path = args.output_dir / "Unihan高频单字多音覆盖审计.tsv"
    fields = list(priority_rows[0]) if priority_rows else []
    with audit_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(priority_rows)

    top30 = priority_rows[:30]
    report = {
        "unihan_kHanyuPinlu_characters": len(raw),
        "unihan_toneless_reading_items": sum(len(value) for value in merged.values()),
        "current_8105_characters_covered": sum(char in current for char in merged),
        "current_8454_pairs_hit": sum(reading in current.get(char, set()) for char, values in merged.items() for reading in values),
        "current_8454_pairs_missing": sum(reading not in current.get(char, set()) for char, values in merged.items() for reading in values),
        "priority_rows": len(priority_rows),
        "priority_rows_covered": sum(row["Unihan覆盖状态"] == "覆盖" for row in priority_rows),
        "top30_covered": sum(row["Unihan覆盖状态"] == "覆盖" for row in top30),
        "top30_consistent_reading_sets": sum(row["读音集合关系"] == "一致" for row in top30),
    }
    (args.output_dir / "Unihan分读音频率审计.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Unihan `kHanyuPinlu` 分读音频率审计",
        "",
        f"- Unihan 字符记录：{report['unihan_kHanyuPinlu_characters']:,}",
        f"- 去调字音项：{report['unihan_toneless_reading_items']:,}",
        f"- 覆盖当前 8105：{report['current_8105_characters_covered']:,}",
        f"- 命中当前 8454 字音项：{report['current_8454_pairs_hit']:,}",
        f"- Unihan 有而当前 8454 无：{report['current_8454_pairs_missing']:,}",
        f"- 431 个高频待分配单字中覆盖：{report['priority_rows_covered']:,}",
        f"- 前 30 项覆盖：{report['top30_covered']}/30",
        f"- 前 30 项读音集合与当前 8454 完全一致：{report['top30_consistent_reading_sets']}/30",
        "",
        "## 前 30 项直接分音证据",
        "",
        "| 排名 | 字 | 未分配频率 | Unihan比例 | Chai频率 | 集合关系 |",
        "|---:|:---:|---:|---|---|---|",
    ]
    for row in top30:
        lines.append(
            f"| {row['影响排名']} | {row['汉字']} | {int(row['未分配频率']):,} | {row['Unihan比例'] or '—'} | {row['Chai去调频率'] or '—'} | {row['读音集合关系']} |"
        )
    lines.extend(["", "该表只提供历史直接语料证据；尚未把比例乘入 SUBTLEX 未分配频率。", ""])
    (args.output_dir / "Unihan分读音频率审计.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
