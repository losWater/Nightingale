#!/usr/bin/env python3
"""把夜莺 0.9.1 正式码表转换为手心输入法挂接表与辅助码表。"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def read_table(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw:
            continue
        parts = raw.split("\t")
        if len(parts) != 2:
            raise ValueError(f"{path}:{line_number}: 应为‘字词<Tab>编码’")
        text, code = parts
        if not text or not code.isascii() or not code.islower() or not code.isalpha():
            raise ValueError(f"{path}:{line_number}: 非法条目：{raw!r}")
        rows.append((text, code))
    return rows


def read_quick_symbols(path: Path) -> list[tuple[str, int, str]]:
    rows: list[tuple[str, int, str]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw:
            continue
        left, separator, text = raw.partition("=")
        code, comma, rank_text = left.rpartition(",")
        if not separator or not comma or not code or not rank_text.isdigit() or not text:
            raise ValueError(f"{path}:{line_number}: 非法快符条目：{raw!r}")
        rows.append((code, int(rank_text), text))
    return rows


def read_short_words(path: Path) -> list[tuple[str, int, str]]:
    output: list[tuple[str, int, str]] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines()[1:]:
        if not raw:
            continue
        text, code, rank_text, _level = raw.split("\t")
        output.append((code, int(rank_text), text))
    return output


def read_extension_characters(path: Path) -> list[tuple[str, int, str]]:
    output: list[tuple[str, int, str]] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines()[1:]:
        if raw:
            character, code, rank_text = raw.split("\t")
            output.append((code, int(rank_text), character))
    return output


def add_attachment_entries(lines: list[str], entries: list[tuple[str, int, str]]) -> list[str]:
    existing: dict[str, list[tuple[int, str]]] = defaultdict(list)
    code_order: list[str] = []
    code_seen: set[str] = set()
    for raw in lines:
        code, right = raw.split("=", 1)
        rank_text, text = right.split(",", 1)
        existing[code].append((int(rank_text), text))
        if code not in code_seen:
            code_order.append(code)
            code_seen.add(code)
    reserved: dict[str, dict[int, str]] = defaultdict(dict)
    for code, rank, text in entries:
        old = reserved[code].get(rank)
        if old is not None and old != text:
            raise ValueError(f"挂接条目自身位置冲突：{code},{rank}={text}；原值={old}")
        reserved[code][rank] = text
        if code not in code_seen:
            code_order.append(code)
            code_seen.add(code)
    output = []
    for code in code_order:
        bucket = dict(reserved.get(code, {}))
        for original_rank, text in existing.get(code, []):
            rank = original_rank
            while rank in bucket and bucket[rank] != text:
                rank += 1
            bucket[rank] = text
        output.extend(f"{code}={rank},{text}" for rank, text in sorted(bucket.items()))
    return output


def read_word_code_fixes(path: Path) -> dict[str, tuple[str, str, int]]:
    rows = path.read_text(encoding="utf-8-sig").splitlines()
    if not rows or rows[0] != "词\t原码\t新码\t新码候选位\t理由":
        raise ValueError(f"{path}: 词码纠错表表头不正确")
    fixes: dict[str, tuple[str, str, int]] = {}
    for line_number, raw in enumerate(rows[1:], 2):
        if not raw:
            continue
        parts = raw.split("\t")
        if len(parts) != 5 or not parts[3].isdigit():
            raise ValueError(f"{path}:{line_number}: 非法词码纠错：{raw!r}")
        word, old_code, new_code, rank_text, _reason = parts
        if word in fixes:
            raise ValueError(f"{path}:{line_number}: 重复纠错词：{word}")
        fixes[word] = (old_code, new_code, int(rank_text))
    return fixes


def build_attachment(
    rows: list[tuple[str, str]],
    quick_symbols: list[tuple[str, int, str]],
    word_code_fixes: dict[str, tuple[str, str, int]],
    single_only: bool = False,
    no_two_character_words: bool = False,
    legacy_short_pairs: set[tuple[str, str]] | None = None,
) -> tuple[list[str], int]:
    buckets: dict[str, dict[int, str]] = {}
    applied_fixes: set[str] = set()
    for text, code in rows:
        if text in word_code_fixes:
            old_code, _new_code, _rank = word_code_fixes[text]
            if code != old_code:
                raise ValueError(f"词码纠错源值不符：{text} 应为 {old_code}，实际为 {code}")
            applied_fixes.add(text)
            continue
        bucket = buckets.setdefault(code, {})
        bucket[len(bucket) + 1] = text
    if applied_fixes != set(word_code_fixes):
        raise ValueError(f"词码纠错未命中：{sorted(set(word_code_fixes) - applied_fixes)}")
    for word, (_old_code, new_code, rank) in word_code_fixes.items():
        bucket = buckets.setdefault(new_code, {})
        for old_rank in sorted((value for value in bucket if value >= rank), reverse=True):
            bucket[old_rank + 1] = bucket.pop(old_rank)
        bucket[rank] = word
    for code, rank, text in quick_symbols:
        bucket = buckets.setdefault(code, {})
        if rank in bucket:
            raise ValueError(f"快符位置与正式字词冲突：{code},{rank}={text}；原值={bucket[rank]}")
        bucket[rank] = text
    quick_entries = set(quick_symbols)
    legacy_short_pairs = legacy_short_pairs or set()
    output = [
        f"{code}={rank},{text}"
        for code, bucket in buckets.items()
        for rank, text in sorted(bucket.items())
        if (
            (not single_only or len(text) == 1 or (code, rank, text) in quick_entries)
            and (
                not no_two_character_words
                or len(text) == 1
                or (text, code) in legacy_short_pairs
                or (len(text) > 1 and len(code) < 4)
                or (code, rank, text) in quick_entries
            )
        )
    ]
    return output, max((int(line.split("=", 1)[1].split(",", 1)[0]) for line in output), default=0)


def build_auxiliary(rows: list[tuple[str, str]]) -> tuple[list[str], int, int]:
    codes_by_character: dict[str, list[str]] = {}
    seen: set[tuple[str, str]] = set()
    four_code_rows = 0
    for text, code in rows:
        if len(text) != 1 or len(code) != 4:
            continue
        four_code_rows += 1
        pair = (text, code[2:])
        if pair in seen:
            continue
        seen.add(pair)
        codes_by_character.setdefault(text, []).append(code[2:])
    output = [f"{text}={' '.join(codes)}" for text, codes in codes_by_character.items()]
    return output, four_code_rows, len(seen)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", type=Path, required=True)
    parser.add_argument("--combined", type=Path, required=True)
    parser.add_argument("--quick", type=Path, required=True)
    parser.add_argument("--short-words", type=Path, required=True)
    parser.add_argument("--extension-characters", type=Path)
    parser.add_argument("--word-code-fixes", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    single_rows = read_table(args.single)
    combined_rows = read_table(args.combined)
    quick_symbols = read_quick_symbols(args.quick)
    short_words = read_short_words(args.short_words)
    extension_characters = read_extension_characters(args.extension_characters) if args.extension_characters else []
    word_code_fixes = read_word_code_fixes(args.word_code_fixes) if args.word_code_fixes else {}
    extension_set = {text for _code, _rank, text in extension_characters}
    short_pairs = {(text, code) for code, _rank, text in short_words}
    # 综合字词主表是候选位唯一真源；旧简词表仅帮助识别既有人工简词。
    attachment_source = [
        row for row in combined_rows
        if row[0] not in extension_set
    ]
    attachment, max_rank = build_attachment(attachment_source, quick_symbols, word_code_fixes)
    no_two_character_words, no_two_character_words_max_rank = build_attachment(
        attachment_source, quick_symbols, word_code_fixes,
        no_two_character_words=True, legacy_short_pairs=short_pairs
    )
    attachment = add_attachment_entries(attachment, extension_characters)
    no_two_character_words = add_attachment_entries(no_two_character_words, extension_characters)
    extension_max_rank = max((rank for _code, rank, _text in extension_characters), default=0)
    max_rank = max(max_rank, extension_max_rank)
    no_two_character_words_max_rank = max(no_two_character_words_max_rank, extension_max_rank)
    # 扩展字是仅供全码输入的次级字符，不进入手心辅助码。
    auxiliary_source = [row for row in single_rows if row[0] not in extension_set]
    auxiliary, four_code_rows, auxiliary_pairs = build_auxiliary(auxiliary_source)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    attachment_path = args.output_dir / "夜莺码v0.9.1电脑手心挂接.txt"
    no_two_character_words_path = args.output_dir / "夜莺码v0.9.1电脑手心无二字词版.txt"
    auxiliary_path = args.output_dir / "夜莺码v0.9.1电脑手心辅助码.txt"
    auxiliary_unicode_path = args.output_dir / "夜莺码v0.9.1电脑手心辅助码_Unicode.txt"
    # 挂接表沿用参考文件的 LF；辅助码按手心导入提示使用“字=码1 码2”，并用 CRLF。
    attachment_path.write_bytes(("\n".join(attachment) + "\n").encode("utf-8"))
    no_two_character_words_path.write_bytes(("\n".join(no_two_character_words) + "\n").encode("utf-8"))
    auxiliary_path.write_bytes(("\r\n".join(auxiliary) + "\r\n").encode("utf-8"))
    # 老式 Windows 软件中的“Unicode 文本”通常指 UTF-16 LE BOM。
    auxiliary_unicode_path.write_bytes(("\r\n".join(auxiliary) + "\r\n").encode("utf-16"))

    attachment_code_count = len(set(code for _, code in combined_rows) | {code for code, _, _ in quick_symbols})
    print(
        f"挂接表：{len(attachment)} 行，{attachment_code_count} 个编码，"
        f"含快符 {len(quick_symbols)} 条，最大候选序号 {max_rank}"
    )
    print(
        f"无二字词版：{len(no_two_character_words)} 行，保留综合表候选位并加入简词，"
        f"含快符 {len(quick_symbols)} 条，最大候选序号 {no_two_character_words_max_rank}"
    )
    print(f"辅助码：输入四码条目 {four_code_rows} 行，{auxiliary_pairs} 个字码组合，合并为 {len(auxiliary)} 个单字")

    manifest_path = next(
        (parent / "发布清单.json" for parent in args.output_dir.parents
         if (parent / "发布清单.json").is_file()),
        args.output_dir.parent / "发布清单.json",
    )
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for path in (attachment_path, no_two_character_words_path, auxiliary_path, auxiliary_unicode_path):
            relative_name = path.relative_to(manifest_path.parent).as_posix()
            manifest["outputs"][relative_name] = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
