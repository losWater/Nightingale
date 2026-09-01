#!/usr/bin/env python3
"""审计虎码词库相对夜莺普通词库缺失的二字词；只分析，不修改正式表。"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml


TONE_RE = re.compile(r"[1-5]$")


def toneless(value: str) -> str:
    return TONE_RE.sub("", value.strip().lower()).replace("u:", "v").replace("ü", "v")


def is_han(char: str) -> bool:
    value = ord(char)
    return (
        0x3400 <= value <= 0x4DBF or 0x4E00 <= value <= 0x9FFF
        or 0xF900 <= value <= 0xFAFF or 0x20000 <= value <= 0x323AF
    )


def read_plain(path: Path) -> list[tuple[str, str]]:
    output = []
    for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        parts = raw.split("\t")
        if len(parts) != 2:
            raise ValueError(f"{path}:{number}: 非法码表行")
        output.append((parts[0], parts[1]))
    return output


def read_short_pairs(path: Path) -> set[tuple[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return {(row["词"], row["简码"]) for row in csv.DictReader(stream, delimiter="\t")}


def load_identity_codes(elements_path: Path, layout_path: Path) -> tuple[dict[tuple[str, str], str], dict[str, set[str]]]:
    elements = yaml.safe_load(elements_path.read_text(encoding="utf-8"))
    layout = yaml.safe_load(layout_path.read_text(encoding="utf-8"))
    mapping = layout["form"]["mapping"]
    identities: dict[tuple[str, str], str] = {}
    readings: dict[str, set[str]] = defaultdict(set)
    for row in elements:
        sequence = row["元素序列"]
        if len(row["词"]) != 1 or len(sequence) < 2:
            continue
        code = mapping[sequence[0]["element"]] + mapping[sequence[1]["element"]]
        reading = row["拼音"]
        identities[(row["词"], reading)] = code
        readings[row["词"]].add(reading)
    return identities, readings


def load_subtlex(path: Path) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            old = result.get(row["Word"])
            if old is None or int(row["WCount"]) > int(old["WCount"]):
                result[row["Word"]] = row
    return result


def load_tiger_two_words(path: Path) -> tuple[set[str], int]:
    result: set[str] = set()
    rows = 0
    in_body = False
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if raw == "...":
            in_body = True
            continue
        if not in_body or not raw:
            continue
        parts = raw.split("\t")
        if len(parts) < 2:
            continue
        word = parts[0]
        if len(word) == 2 and all(is_han(char) for char in word):
            rows += 1
            result.add(word)
    return result, rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tiger", type=Path, required=True)
    parser.add_argument("--combined", type=Path, required=True)
    parser.add_argument("--short-words", type=Path, required=True)
    parser.add_argument("--extension", type=Path, required=True)
    parser.add_argument("--elements", type=Path, required=True)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--subtlex", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    combined = read_plain(args.combined)
    short_pairs = read_short_pairs(args.short_words)
    short_words = {word for word, _code in short_pairs}
    ordinary_words = {text for text, code in combined if len(text) == 2 and (text, code) not in short_pairs}
    buckets: dict[str, list[str]] = defaultdict(list)
    for text, code in combined:
        buckets[code].append(text)
    with args.extension.open("r", encoding="utf-8-sig", newline="") as stream:
        extension_chars = {row["字"] for row in csv.DictReader(stream, delimiter="\t")}
    identities, readings = load_identity_codes(args.elements, args.layout)
    subtlex = load_subtlex(args.subtlex)
    tiger_words, tiger_rows = load_tiger_two_words(args.tiger)
    missing = sorted(tiger_words - ordinary_words)

    rows: list[dict[str, str]] = []
    for word in missing:
        source = subtlex.get(word)
        pinyin = source["Pinyin"] if source else ""
        frequency = int(source["WCount"]) if source else 0
        code = ""
        evidence = ""
        note = ""
        if source is None:
            options = [sorted(readings.get(char, set())) for char in word]
            if all(len(values) == 1 for values in options):
                chosen = [values[0] for values in options]
                code = "".join(identities.get((char, reading), "") for char, reading in zip(word, chosen))
                if len(code) == 4:
                    pinyin = " ".join(chosen)
                    evidence = "单字均为唯一读音；无整词频率"
                else:
                    evidence = "单字读音无法映射"
            else:
                evidence = "无SUBTLEX；含多音字待审"
                note = " ".join(f"{char}:{'/'.join(values) or '无'}" for char, values in zip(word, options))
        else:
            syllables = pinyin.split()
            options = [part.split("/") for part in syllables]
            if len(syllables) != 2:
                evidence = "SUBTLEX音节数不符"
            elif any(len(values) != 1 for values in options):
                evidence = "SUBTLEX读音多选；待审"
            else:
                chosen = [toneless(values[0]) for values in options]
                missing_maps = [f"{char}/{reading}" for char, reading in zip(word, chosen) if (char, reading) not in identities]
                if missing_maps:
                    evidence = "SUBTLEX读音无法映射"
                    note = " ".join(missing_maps)
                else:
                    code = "".join(identities[(char, reading)] for char, reading in zip(word, chosen))
                    evidence = "SUBTLEX逐字唯一读音"

        existing = buckets.get(code, []) if code else []
        exact_short = code != "" and (word, code) in short_pairs
        if exact_short:
            action = "已有同码简词；不应重复加入"
        elif evidence == "SUBTLEX逐字唯一读音" and frequency >= 10 and any(char.isupper() for char in pinyin):
            action = "疑似专名；暂缓"
        elif evidence == "SUBTLEX逐字唯一读音" and frequency >= 10:
            action = "高置信候选"
        elif evidence == "SUBTLEX逐字唯一读音":
            action = "低频候选"
        elif evidence == "单字均为唯一读音；无整词频率":
            action = "无词频候选；人工判断词性"
        else:
            action = "读音待审"
        core_chars = [x for x in existing if len(x) == 1 and x not in extension_chars]
        ext_chars = [x for x in existing if len(x) == 1 and x in extension_chars]
        words = [x for x in existing if len(x) > 1 and (x, code) not in short_pairs]
        shorts = [x for x in existing if (x, code) in short_pairs]
        if not code:
            collision = "未定码"
        elif not existing:
            collision = "空码"
        else:
            collision = "+".join(label for label, values in (
                ("核心字", core_chars), ("普通词", words), ("简词", shorts), ("扩展字", ext_chars)
            ) if values)
        rows.append({
            "词": word, "参考虎码": "已忽略", "现有简词": "是" if word in short_words else "否",
            "SUBTLEX拼音": pinyin, "SUBTLEX词频": str(frequency), "夜莺建议码": code,
            "读音证据": evidence, "冲突类型": collision, "现有码位候选数": str(len(existing)),
            "预计追加候选位": str(len(existing) + 1) if code and not exact_short else "",
            "现有候选": "、".join(existing), "处理建议": action, "备注": note,
        })

    priority = {"高置信候选": 0, "疑似专名；暂缓": 1, "低频候选": 2,
                "无词频候选；人工判断词性": 3, "已有同码简词；不应重复加入": 4, "读音待审": 5}
    rows.sort(key=lambda row: (priority[row["处理建议"]], -int(row["SUBTLEX词频"]), row["词"]))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with (args.output_dir / "虎码缺失二字词_完整审计.tsv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t")
        writer.writeheader(); writer.writerows(rows)
    with (args.output_dir / "虎码缺失二字词_完整审计.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    review = [row for row in rows if row["处理建议"] == "高置信候选"][:1000]
    with (args.output_dir / "优先复核前1000.tsv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t")
        writer.writeheader(); writer.writerows(review)
    conservative = [row for row in rows if row["处理建议"] == "高置信候选" and int(row["SUBTLEX词频"]) >= 50]
    with (args.output_dir / "保守候选_词频至少50.tsv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t")
        writer.writeheader(); writer.writerows(conservative)
    with (args.output_dir / "保守候选_词频至少50.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(conservative)

    actions = Counter(row["处理建议"] for row in rows)
    collisions = Counter(row["冲突类型"] for row in rows if row["处理建议"] == "高置信候选")
    high = [row for row in rows if row["处理建议"] == "高置信候选"]
    lines = [
        "# 虎码缺失二字词审计（未实装）", "",
        f"- 虎码二字汉字词：{len(tiger_words):,} 个（源表 {tiger_rows:,} 行）；",
        f"- 夜莺现有普通二字词：{len(ordinary_words):,} 个；",
        f"- 忽略夜莺简词层后，虎码侧新增候选：{len(missing):,} 个；",
        *[f"- {name}：{count:,} 个；" for name, count in actions.most_common()],
        "", "## 高置信候选的碰撞情况", "",
        *[f"- {name}：{count:,} 个；" for name, count in collisions.most_common()],
        "", "## 按 SUBTLEX 词频排序的前 100 个高置信候选", "",
        "|词|拼音|建议码|词频|冲突|预计位|现有候选|", "|---|---|---|---:|---|---:|---|",
        *[f"|{r['词']}|{r['SUBTLEX拼音']}|{r['夜莺建议码']}|{r['SUBTLEX词频']}|{r['冲突类型']}|{r['预计追加候选位']}|{r['现有候选']}|" for r in high[:100]],
        "", "本目录仅为分析结果，没有修改任何正式码表。虎码编码列全程未参与夜莺编码推导。", "",
    ]
    (args.output_dir / "结果摘要.md").write_text("\n".join(lines), encoding="utf-8")
    print({"tiger_two_words": len(tiger_words), "ordinary_two_words": len(ordinary_words),
           "missing": len(missing), "actions": dict(actions), "high_collisions": dict(collisions)})


if __name__ == "__main__":
    main()
