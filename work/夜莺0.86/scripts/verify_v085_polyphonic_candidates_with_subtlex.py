#!/usr/bin/env python3
"""用 SUBTLEX 整词拼音验证夜莺 0.8.5 多音词初筛候选。"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

import yaml


TONE_RE = re.compile(r"[1-5]$")


def toneless(value: str) -> str:
    return TONE_RE.sub("", value.strip().lower()).replace("u:", "v").replace("ü", "v")


def encode_word(word: str, sounds: list[str]) -> str:
    if len(word) == 2:
        return sounds[0] + sounds[1]
    if len(word) == 3:
        return sounds[0][0] + sounds[1][0] + sounds[2]
    return "".join(code[0] for code in sounds[:3] + sounds[-1:])


def load_identity_codes(elements_path: Path, layout_path: Path) -> dict[tuple[str, str], str]:
    elements = yaml.safe_load(elements_path.read_text(encoding="utf-8"))
    layout = yaml.safe_load(layout_path.read_text(encoding="utf-8"))
    mapping = layout["form"]["mapping"]
    result: dict[tuple[str, str], str] = {}
    for row in elements:
        sequence = row["元素序列"]
        if len(sequence) < 2:
            continue
        first, second = sequence[0]["element"], sequence[1]["element"]
        result[(row["词"], row["拼音"])] = mapping[first] + mapping[second]
    return result


def load_subtlex(path: Path) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            result[row["Word"]] = row
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--elements", type=Path, required=True)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--subtlex", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    identity_codes = load_identity_codes(args.elements, args.layout)
    subtlex = load_subtlex(args.subtlex)
    with args.candidates.open("r", encoding="utf-8-sig", newline="") as handle:
        candidates = list(csv.DictReader(handle, delimiter="\t"))

    output: list[dict[str, str]] = []
    counts: Counter[str] = Counter()
    for source in candidates:
        word = source["词"]
        row = subtlex.get(word)
        pinyin = row["Pinyin"] if row else ""
        frequency = row["WCount"] if row else ""
        predicted = ""
        reason = ""
        if row is None:
            status = "无SUBTLEX词条"
        else:
            syllables = pinyin.split()
            options = [part.split("/") for part in syllables]
            if len(syllables) != len(word):
                status = "SUBTLEX音节数不符"
            elif any(len(items) != 1 for items in options):
                status = "SUBTLEX读音多选"
            else:
                readings = [toneless(items[0]) for items in options]
                missing = [f"{char}/{reading}" for char, reading in zip(word, readings) if (char, reading) not in identity_codes]
                if missing:
                    status = "SUBTLEX读音无法映射"
                    reason = " ".join(missing)
                else:
                    sounds = [identity_codes[(char, reading)] for char, reading in zip(word, readings)]
                    predicted = encode_word(word, sounds)
                    if predicted == source["当前码"]:
                        status = "唯一读音支持当前码"
                    elif predicted == source["参考建议码"]:
                        status = "唯一读音确认参考建议"
                    else:
                        status = "唯一读音指向第三码"
        counts[status] += 1
        output.append({
            "词": word,
            "词长": source["词长"],
            "当前码": source["当前码"],
            "简单鹤初筛建议": source["参考建议码"],
            "SUBTLEX拼音": pinyin,
            "SUBTLEX推导码": predicted,
            "SUBTLEX词频": frequency,
            "证据分级": status,
            "备注": reason,
        })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    fields = ["词", "词长", "当前码", "简单鹤初筛建议", "SUBTLEX拼音", "SUBTLEX推导码", "SUBTLEX词频", "证据分级", "备注"]
    output.sort(key=lambda row: (
        0 if row["证据分级"] == "唯一读音确认参考建议" else 1,
        -int(row["SUBTLEX词频"] or 0),
        row["词"],
    ))
    with (args.output_dir / "SUBTLEX读音证据分级.tsv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(output)

    confirmed = [row for row in output if row["证据分级"] == "唯一读音确认参考建议"]
    first_batch = [
        row for row in confirmed
        if int(row["SUBTLEX词频"]) >= 10 and not any(char.isupper() for char in row["SUBTLEX拼音"])
    ]
    proposal_fields = ["词", "当前码", "建议码", "SUBTLEX拼音", "SUBTLEX词频", "处理建议"]
    with (args.output_dir / "第一批高置信度纠错建议.tsv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=proposal_fields, delimiter="\t")
        writer.writeheader()
        for row in first_batch:
            writer.writerow({
                "词": row["词"],
                "当前码": row["当前码"],
                "建议码": row["SUBTLEX推导码"],
                "SUBTLEX拼音": row["SUBTLEX拼音"],
                "SUBTLEX词频": row["SUBTLEX词频"],
                "处理建议": "第一批；应用前抽查并按基础词表原顺序重排新码位候选",
            })
    lines = [
        "# 夜莺 0.8.5 多音词 SUBTLEX 证据复核",
        "",
        f"- 初筛候选：{len(output):,} 条；",
        *[f"- {status}：{count:,} 条；" for status, count in counts.most_common()],
        "",
        f"- 第一批建议范围（唯一读音确认、词频≥10、排除拼音大写专名）：{len(first_batch):,} 条。",
        "",
        "`唯一读音确认参考建议` 表示 SUBTLEX 给出逐字唯一读音，且按夜莺正式音码映射后与初筛建议一致；这是确认度最高的一档，但批量改码前仍建议抽查专名和异读。",
        "",
        "## 按 SUBTLEX 词频排序的前 50 条确认候选",
        "",
        "| 词 | 当前码 | 推导码 | SUBTLEX 拼音 | 词频 |",
        "|---|---|---|---|---:|",
        *[
            f"| {row['词']} | {row['当前码']} | {row['SUBTLEX推导码']} | {row['SUBTLEX拼音']} | {row['SUBTLEX词频']} |"
            for row in confirmed[:50]
        ],
        "",
        "完整证据见 `SUBTLEX读音证据分级.tsv`；第一批清单见 `第一批高置信度纠错建议.tsv`。本轮不自动修改正式词码。",
        "",
    ]
    (args.output_dir / "SUBTLEX证据摘要.md").write_text("\n".join(lines), encoding="utf-8")
    print(dict(counts))


if __name__ == "__main__":
    main()
