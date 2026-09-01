# -*- coding: utf-8 -*-
"""用统一词库和统一组词规则，从任意单字码表生成词库码表。

默认规则：
  二字：两个字各取前2码
  三字：三个字各取首码 + 末字第2码
  四字及以上：前三字各首码 + 末字首码

输入行可用制表符或空白分隔，并自动判断“字 码”或“码 字”。单字存在
简码和全码时，默认选择最长码；同长度多码时保留文件中最先出现的一项。
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


HAN_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U000323af]")


def fields(line: str) -> list[str]:
    return line.strip().split()


def looks_code(text: str, alphabet: set[str] | None = None) -> bool:
    if not text or len(text) > 32 or any(char.isspace() for char in text):
        return False
    if any(HAN_RE.fullmatch(char) for char in text):
        return False
    if alphabet is not None:
        return all(char in alphabet for char in text)
    return text.isascii() and text.isprintable() and not text.isdigit()


def looks_char(text: str) -> bool:
    return len(text) == 1 and bool(HAN_RE.fullmatch(text))


def parse_char_table(path: Path, char_column: int | None, code_column: int | None, alphabet: set[str] | None):
    candidates: dict[str, list[tuple[int, str]]] = defaultdict(list)
    rejected = 0
    for order, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines()):
        row = fields(line)
        if not row or line.lstrip().startswith(("#", "//")):
            continue
        if char_column is not None and code_column is not None:
            if max(char_column, code_column) >= len(row):
                rejected += 1; continue
            char, code = row[char_column], row[code_column]
        elif len(row) >= 2 and looks_char(row[0]) and looks_code(row[1], alphabet):
            char, code = row[0], row[1]
        elif len(row) >= 2 and looks_code(row[0], alphabet) and looks_char(row[1]):
            char, code = row[1], row[0]
        else:
            rejected += 1; continue
        if not looks_char(char) or not looks_code(code, alphabet):
            rejected += 1; continue
        candidates[char].append((order, code))

    # 最长者视为全码；同长度时尊重原表顺序。
    selected = {
        char: sorted(items, key=lambda item: (-len(item[1]), item[0]))[0][1]
        for char, items in candidates.items()
    }
    multi_full = {
        char: [code for _, code in items if len(code) == max(len(x[1]) for x in items)]
        for char, items in candidates.items()
        if len({code for _, code in items if len(code) == max(len(x[1]) for x in items)}) > 1
    }
    return selected, multi_full, rejected


def extract_word(row: list[str]) -> str | None:
    # 词库可自带旧方案编码或频率；只取第一个纯汉字段，其他列全部丢弃。
    return next((item for item in row if len(item) >= 2 and all(HAN_RE.fullmatch(c) for c in item)), None)


def encode_word(word: str, codes: dict[str, str]) -> str | None:
    try:
        char_codes = [codes[c] for c in word]
    except KeyError:
        return None
    if len(word) == 2:
        if len(char_codes[0]) < 2 or len(char_codes[1]) < 2: return None
        return char_codes[0][:2] + char_codes[1][:2]
    if len(word) == 3:
        if len(char_codes[0]) < 1 or len(char_codes[1]) < 1 or len(char_codes[2]) < 2: return None
        return char_codes[0][0] + char_codes[1][0] + char_codes[2][0] + char_codes[2][1]
    if len(word) >= 4:
        selected = char_codes[:3] + [char_codes[-1]]
        if any(not code for code in selected): return None
        return "".join(code[0] for code in selected)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("char_table", type=Path)
    ap.add_argument("lexicon", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--char-column", type=int, help="字列，0起算；须与--code-column同时使用")
    ap.add_argument("--code-column", type=int, help="码列，0起算；须与--char-column同时使用")
    ap.add_argument("--length", type=int, choices=[2, 3, 4], help="只生成指定词长；4表示四字及以上")
    ap.add_argument("--alphabet", help="显式允许的码元；纯数字或非ASCII方案必须指定")
    args = ap.parse_args()
    if (args.char_column is None) != (args.code_column is None):
        ap.error("--char-column 和 --code-column 必须同时使用")

    codes, multi_full, rejected_rows = parse_char_table(
        args.char_table, args.char_column, args.code_column, set(args.alphabet) if args.alphabet else None
    )
    seen_words, output_rows, missing = set(), [], Counter()
    source_rows = 0
    for line in args.lexicon.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        row = fields(line)
        if not row or line.lstrip().startswith(("#", "//")):
            continue
        word = extract_word(row)
        if not word or word in seen_words:
            continue
        source_rows += 1
        seen_words.add(word)
        bucket = 4 if len(word) >= 4 else len(word)
        if len(word) < 2 or (args.length and bucket != args.length):
            continue
        absent = [c for c in word if c not in codes]
        if absent:
            missing.update(absent); continue
        code = encode_word(word, codes)
        if code is None:
            continue
        output_rows.append((word, code))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(f"{word}\t{code}" for word, code in output_rows) + "\n", encoding="utf-8")
    slots = Counter(code for _, code in output_rows)
    report = {
        "char_table": str(args.char_table.resolve()),
        "lexicon": str(args.lexicon.resolve()),
        "output": str(args.output.resolve()),
        "single_characters": len(codes),
        "alphabet": "".join(sorted({symbol for code in codes.values() for symbol in code})),
        "alphabet_size": len({symbol for code in codes.values() for symbol in code}),
        "ambiguous_full_code_characters": len(multi_full),
        "rejected_char_table_rows": rejected_rows,
        "unique_source_words": source_rows,
        "encoded_words": len(output_rows),
        "unique_code_slots": len(slots),
        "collision_slots": sum(n > 1 for n in slots.values()),
        "collision_words": sum(n - 1 for n in slots.values() if n > 1),
        "maximum_slot_size": max(slots.values(), default=0),
        "new_slot_ratio": len(slots) / len(output_rows) if output_rows else 0,
        "missing_unique_characters": len(missing),
        "most_common_missing": missing.most_common(30),
    }
    report_path = args.output.with_suffix(args.output.suffix + ".report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"REPORT={report_path}")


if __name__ == "__main__":
    main()
