#!/usr/bin/env python3
"""审计扩展字的 Chai/Unihan 普通话读音覆盖，不读取旧扩展码。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


TONE_DIGIT = re.compile(r"[1-5]$")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def toneless(value: str) -> str:
    value = TONE_DIGIT.sub("", value.strip().lower()).replace("u:", "ü")
    decomposed = unicodedata.normalize("NFD", value)
    result: list[str] = []
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
        result.append("v" if char == "u" and "\u0308" in marks else char)
        index = cursor
    return "".join(result)


def read_chars(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [row["汉字"] for row in csv.DictReader(stream, delimiter="\t")]


def read_chai(path: Path, charset: set[str]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        fields = raw.split("\t")
        if len(fields) < 2 or fields[0] not in charset or len(fields[0]) != 1:
            continue
        reading = toneless(fields[1])
        if reading and " " not in reading:
            result[fields[0]].add(reading)
    return result


def read_unihan(path: Path, charset: set[str]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.startswith("U+"):
            continue
        codepoint, field, value = raw.split("\t", 2)
        char = chr(int(codepoint[2:], 16))
        if char not in charset or field != "kMandarin":
            continue
        for reading in value.split():
            normalized = toneless(reading)
            if normalized:
                result[char].add(normalized)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--splits", type=Path, required=True)
    parser.add_argument("--chai-dictionary", type=Path, required=True)
    parser.add_argument("--unihan-readings", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for key in ("splits", "chai_dictionary", "unihan_readings", "output_dir"):
        setattr(args, key, getattr(args, key).resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)

    chars = read_chars(args.splits)
    charset = set(chars)
    chai = read_chai(args.chai_dictionary, charset)
    unihan = read_unihan(args.unihan_readings, charset)
    rows = []
    for char in chars:
        c = sorted(chai.get(char, set()))
        u = sorted(unihan.get(char, set()))
        rows.append({
            "汉字": char,
            "Chai读音": " ".join(c),
            "Unihan普通话": " ".join(u),
            "采用状态": "Chai" if c else "待补",
            "集合关系": (
                "一致" if c and set(c) == set(u)
                else "Unihan未覆盖" if c and not u
                else "Chai未覆盖" if not c and u
                else "存在差异" if c or u else "均未覆盖"
            ),
        })
    out = args.output_dir / "扩展字读音覆盖审计.tsv"
    with out.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    report = {
        "characters": len(chars),
        "chai_covered_characters": sum(bool(chai.get(c)) for c in chars),
        "chai_reading_pairs": sum(len(chai.get(c, set())) for c in chars),
        "chai_missing_characters": sum(not chai.get(c) for c in chars),
        "unihan_kMandarin_covered_characters": sum(bool(unihan.get(c)) for c in chars),
        "same_reading_sets": sum(bool(chai.get(c)) and chai[c] == unihan.get(c, set()) for c in chars),
        "different_nonempty_sets": sum(bool(chai.get(c)) and bool(unihan.get(c)) and chai[c] != unihan[c] for c in chars),
        "inputs": {
            args.splits.name: sha256(args.splits),
            "dictionary.txt": sha256(args.chai_dictionary),
            "Unihan_Readings.txt": sha256(args.unihan_readings),
        },
        "output_sha256": sha256(out),
        "old_extension_codes_read": False,
    }
    (args.output_dir / "扩展字读音覆盖审计.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
