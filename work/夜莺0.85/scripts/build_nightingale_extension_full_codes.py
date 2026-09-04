#!/usr/bin/env python3
"""由现行拆分、Chai读音和0.9布局生成扩展字理性全码候选。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "work" / "重开工程"
sys.path.insert(0, str(PROJECT / "scripts"))
import audit_manual_split_propagation as audit  # noqa: E402


INITIAL_RE = re.compile(r"^([aeioubpmfdtnlgkhjqxzcsryw]h?|^).+$")
ZERO_TWO_RE = re.compile(r"^[aeiouv](.)[1-5]$")
FINAL_RE = re.compile(r"^.*?([aeiouv].*|m|ng?)[1-5]$")
TONE_RE = re.compile(r"[1-5]$")
STROKE_ELEMENTS = {"横": "1", "竖": "2", "撇": "3", "点": "4", "折": "5"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_mapping(mapping: dict[str, object], element: str, resolved_names: dict[str, str]) -> str:
    element = STROKE_ELEMENTS.get(element, element)
    element = resolved_names.get(element, element)
    seen: set[str] = set()
    while True:
        if element in seen:
            raise ValueError(f"键位映射成环：{element}")
        seen.add(element)
        value = mapping.get(element)
        if isinstance(value, str):
            if len(value) != 1:
                raise ValueError(f"非法键位：{element} -> {value}")
            return value
        if isinstance(value, dict) and value.get("element") is not None:
            element = str(value["element"])
            continue
        raise ValueError(f"元素没有0.9键位：{ascii(element)}")


def sound_elements(toned: str) -> tuple[str, str, str]:
    source = toned.strip().lower().replace("u:", "ü")
    decomposed = unicodedata.normalize("NFD", source)
    value_parts: list[str] = []
    index = 0
    while index < len(decomposed):
        char = decomposed[index]
        if unicodedata.combining(char):
            index += 1
            continue
        marks: list[str] = []
        cursor = index + 1
        while cursor < len(decomposed) and unicodedata.combining(decomposed[cursor]):
            marks.append(decomposed[cursor]); cursor += 1
        value_parts.append("v" if char == "u" and "\u0308" in marks else char)
        index = cursor
    value = "".join(value_parts)
    if not TONE_RE.search(value):
        value += "1"
    plain = TONE_RE.sub("", value)
    initial_match = INITIAL_RE.match(value)
    if not initial_match:
        raise ValueError(f"无法提取声母：{ascii(toned)}")
    initial = initial_match.group(1)
    zero_two = ZERO_TWO_RE.match(value)
    if zero_two:
        final = zero_two.group(1)
    else:
        final_match = FINAL_RE.match(value)
        if not final_match:
            raise ValueError(f"无法提取韵母：{ascii(toned)}")
        final = final_match.group(1)
    return plain, f"szm-{initial}", f"mzm-{final}"


def load_splits(path: Path) -> dict[str, tuple[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return {row["汉字"]: (row["编码首根"], row["编码末根"])
                for row in csv.DictReader(stream, delimiter="\t")}


def load_dictionary_primary(path: Path, charset: set[str]) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        fields = raw.split("\t")
        if len(fields) < 2 or fields[0] not in charset or len(fields[0]) != 1:
            continue
        if fields[0] not in result:
            plain, _, _ = sound_elements(fields[1])
            result[fields[0]] = (plain, fields[1])
    return result


def load_unihan_primary(path: Path, charset: set[str]) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if "\tkMandarin\t" not in raw:
            continue
        codepoint, _, value = raw.split("\t", 2)
        char = chr(int(codepoint[2:], 16))
        if char in charset:
            source = value.split()[0]
            plain, _, _ = sound_elements(source)
            result[char] = (plain, source)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--splits", type=Path, required=True)
    parser.add_argument("--dictionary", type=Path, required=True)
    parser.add_argument("--unihan-readings", type=Path, required=True)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for name in ("splits", "dictionary", "unihan_readings", "layout", "output_dir"):
        setattr(args, name, getattr(args, name).resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)

    splits = load_splits(args.splits)
    chai_primary = load_dictionary_primary(args.dictionary, set(splits))
    unihan_primary = load_unihan_primary(args.unihan_readings, set(splits))
    layout = yaml.safe_load(args.layout.read_text(encoding="utf-8"))
    mapping = layout["form"]["mapping"]
    baseline = yaml.safe_load(audit.BASELINE_PATH.read_text(encoding="utf-8"))
    by_name, _ = audit.repertoire_maps(baseline)
    resolved_names = {element: audit.resolve(element, by_name) for element in splits.values() for element in element}
    rows: list[dict[str, str]] = []
    pairs: set[tuple[str, str]] = set()
    for char, (head, tail) in splits.items():
        selected = unihan_primary.get(char) or chai_primary.get(char)
        if selected is None:
            continue
        plain, source_reading = selected
        _, initial_element, final_element = sound_elements(source_reading)
        code = "".join([
            resolve_mapping(mapping, initial_element, resolved_names),
            resolve_mapping(mapping, final_element, resolved_names),
            resolve_mapping(mapping, head, resolved_names),
            resolve_mapping(mapping, tail, resolved_names),
        ])
        if len(code) != 4 or not code.isascii() or not code.islower():
            raise ValueError(f"非法全码：{char} {plain} {code}")
        pair = (char, plain)
        if pair in pairs:
            raise ValueError(f"重复字音：{char} {plain}")
        pairs.add(pair)
        rows.append({
            "汉字": char, "拼音": plain, "全码": code,
            "编码首根": head, "编码末根": tail,
            "读音来源": "Unihan kMandarin" if char in unihan_primary else "Chai dictionary fallback",
            "来源读音": source_reading,
        })
    missing = [char for char in splits if char not in unihan_primary and char not in chai_primary]
    if missing:
        raise ValueError("扩展字缺读音：" + " ".join(missing[:30]))

    output = args.output_dir / "扩展字全码_结构候选.tsv"
    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    report = {
        "characters": len(splits),
        "character_reading_codes": len(rows),
        "unihan_primary": sum(row["读音来源"] == "Unihan kMandarin" for row in rows),
        "chai_fallback": sum(row["读音来源"] == "Chai dictionary fallback" for row in rows),
        "ai_traditional": [row for row in rows if row["汉字"] == "愛"],
        "inputs": {
            args.splits.name: sha256(args.splits),
            "dictionary.txt": sha256(args.dictionary),
            "Unihan_Readings.txt": sha256(args.unihan_readings),
            args.layout.name: sha256(args.layout),
            str(audit.BASELINE_PATH.relative_to(ROOT)): sha256(audit.BASELINE_PATH),
            str(audit.NAME_ALIASES_PATH.relative_to(ROOT)): sha256(audit.NAME_ALIASES_PATH),
        },
        "outputs": {
            output.name: sha256(output),
        },
        "old_extension_codes_read": False,
    }
    (args.output_dir / "扩展字全码_生成清单.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
