#!/usr/bin/env python3
"""从字词混合码表中批量提取纯单字主码，并保留全部单字编码证据。"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


HAN = re.compile(r"^[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U000323af]$")


def looks_code(value: str, alphabet: set[str] | None = None) -> bool:
    """识别码串；不把码元限制为26字母，兼容32键等标点码元方案。"""
    if not value or len(value) > 32 or any(char.isspace() for char in value):
        return False
    if any(HAN.fullmatch(char) for char in value):
        return False
    if alphabet is not None:
        return all(char in alphabet for char in value)
    return value.isascii() and value.isprintable() and not value.isdigit()


def decode(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16"), "utf-16"
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace"), "utf-8-replace"


def parse(path: Path, alphabet: set[str] | None = None):
    text, encoding = decode(path)
    entries: dict[str, list[dict]] = defaultdict(list)
    rejected = Counter()
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            rejected["空行"] += 1
            continue
        if stripped.startswith(("#", "//", ";", "---", "...")) or stripped.startswith(("name:", "version:", "sort:", "columns:")):
            rejected["注释或头部"] += 1
            continue
        # 逗号、分号和句点本身都可能是码元，不能把它们当作通用分隔符。
        fields = stripped.split()
        chars = [(index, value) for index, value in enumerate(fields) if HAN.fullmatch(value)]
        codes = [(index, value) for index, value in enumerate(fields) if looks_code(value, alphabet)]
        if not chars:
            rejected["无纯单字"] += 1
            continue
        if not codes:
            rejected["无字母编码"] += 1
            continue
        # 优先选择与单字相邻的编码；常见“字 码”和“码 字”均自然命中。
        char_index, char = chars[0]
        code_index, code = min(codes, key=lambda item: (abs(item[0] - char_index), item[0]))
        entries[char].append({"code": code, "line": lineno, "raw": stripped,
                              "char_column": char_index, "code_column": code_index})
    return entries, rejected, encoding, len(text.splitlines())


def clean_one(path: Path, output: Path, alphabet: set[str] | None = None) -> dict:
    entries, rejected, encoding, total_lines = parse(path, alphabet)
    all_rows = []
    primary = {}
    multi_full = {}
    for char, items in entries.items():
        dedup = []
        seen = set()
        for item in items:
            if item["code"] not in seen:
                dedup.append(item)
                seen.add(item["code"])
        max_length = max((len(item["code"]) for item in dedup), default=0)
        full = [item for item in dedup if len(item["code"]) == max_length]
        primary[char] = full[0]["code"]
        if len(full) > 1:
            multi_full[char] = [item["code"] for item in full]
        for order, item in enumerate(dedup, 1):
            all_rows.append({"character": char, "code": item["code"], "length": len(item["code"]),
                             "is_full": int(len(item["code"]) == max_length),
                             "is_primary": int(item["code"] == primary[char]),
                             "source_line": item["line"], "source_order": order})

    stem = path.stem
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{stem}_纯单字主码.txt").write_text(
        "\n".join(f"{char}\t{code}" for char, code in primary.items()) + "\n", encoding="utf-8"
    )
    fields = ["character", "code", "length", "is_full", "is_primary", "source_line", "source_order"]
    with (output / f"{stem}_全部单字编码.tsv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(all_rows)
    report = {
        "source": str(path.resolve()), "detected_encoding": encoding, "total_lines": total_lines,
        "unique_characters": len(primary), "all_unique_char_codes": len(all_rows),
        "multi_full_characters": len(multi_full), "multi_full_examples": dict(list(multi_full.items())[:100]),
        "primary_length_distribution": dict(sorted(Counter(map(len, primary.values())).items())),
        "alphabet": "".join(sorted({symbol for row in all_rows for symbol in row["code"]})),
        "alphabet_size": len({symbol for row in all_rows for symbol in row["code"]}),
        "rejected": dict(rejected),
    }
    (output / f"{stem}_清洗报告.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="单个码表文件或原始码表目录")
    parser.add_argument("output", type=Path, help="清洗结果目录")
    parser.add_argument("--alphabet", help="显式允许的码元，例如 abcdefghijklmnopqrstuvwxyz;,./")
    args = parser.parse_args()
    paths = [args.input] if args.input.is_file() else sorted(
        path for path in args.input.rglob("*") if path.is_file() and path.suffix.lower() in {".txt", ".tsv", ".csv", ".dict", ".yaml", ".yml"}
    )
    summary = {}
    for path in paths:
        destination = args.output / path.stem
        try:
            summary[path.name] = clean_one(path, destination, set(args.alphabet) if args.alphabet else None)
            print(f"{path.name}: {summary[path.name]['unique_characters']}字")
        except Exception as error:
            summary[path.name] = {"source": str(path), "error": repr(error)}
            print(f"{path.name}: ERROR {error}")
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "批量清洗汇总.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
