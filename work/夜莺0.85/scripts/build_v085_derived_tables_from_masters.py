#!/usr/bin/env python3
"""仅以正式单字主表和综合字词主表生成 0.8.5 搜狗派生表。"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import OrderedDict
from pathlib import Path


def read_plain(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        parts = raw.split("\t")
        if len(parts) != 2 or not parts[0] or not parts[1].isalpha() or not parts[1].islower():
            raise ValueError(f"{path}:{line_number}: 非法主表行")
        rows.append((parts[0], parts[1]))
    return rows


def slots(rows: list[tuple[str, str]]) -> OrderedDict[str, list[str]]:
    result: OrderedDict[str, list[str]] = OrderedDict()
    for text, code in rows:
        result.setdefault(code, []).append(text)
    return result


def read_quick(path: Path) -> list[tuple[str, int, str]]:
    output: list[tuple[str, int, str]] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if not raw:
            continue
        left, text = raw.split("=", 1)
        code, rank = left.rsplit(",", 1)
        output.append((code, int(rank), text))
    return output


def read_short_words(path: Path) -> list[tuple[str, int, str]]:
    rows = path.read_text(encoding="utf-8-sig").splitlines()
    output: list[tuple[str, int, str]] = []
    for raw in rows[1:]:
        if not raw:
            continue
        text_value, code, rank_text, _level = raw.split("\t")
        output.append((code, int(rank_text), text_value))
    return output


def read_extension_characters(path: Path) -> list[tuple[str, int, str]]:
    output: list[tuple[str, int, str]] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines()[1:]:
        if raw:
            character, code, rank_text = raw.split("\t")
            output.append((code, int(rank_text), character))
    return output


def render_sogou(
    source: OrderedDict[str, list[str]], headers: list[str], sparse_single_only: bool
) -> list[str]:
    lines = list(headers)
    if headers:
        lines.append("")
    for code, items in source.items():
        for rank, text in enumerate(items, 1):
            if not sparse_single_only or len(text) == 1:
                lines.append(f"{code},{rank}={text}")
    return lines


def is_short_word(text: str, code: str, legacy_pairs: set[tuple[str, str]]) -> bool:
    """简词身份由主表内容决定；旧简词表只用于识别既有人工简词。"""
    return len(text) > 1 and ((text, code) in legacy_pairs or len(code) < 4)


def render_no_two_words(
    source: OrderedDict[str, list[str]], headers: list[str], legacy_pairs: set[tuple[str, str]]
) -> list[str]:
    lines = list(headers)
    if headers:
        lines.append("")
    for code, items in source.items():
        for rank, text in enumerate(items, 1):
            if len(text) == 1 or is_short_word(text, code, legacy_pairs):
                lines.append(f"{code},{rank}={text}")
    return lines


def add_quick(lines: list[str], quick: list[tuple[str, int, str]], add_header: bool) -> list[str]:
    headers = [line for line in lines if not line or line.startswith(";")]
    data = [line for line in lines if line and not line.startswith(";")]
    occupied: dict[tuple[str, int], str] = {}
    code_order: list[str] = []
    for raw in data:
        left, text = raw.split("=", 1)
        code, rank_text = left.rsplit(",", 1)
        if code not in code_order:
            code_order.append(code)
        occupied[(code, int(rank_text))] = text
    for code, rank, text in quick:
        if (code, rank) in occupied:
            raise ValueError(f"快符位置冲突：{code},{rank}={text}；原值={occupied[(code, rank)]}")
        occupied[(code, rank)] = text
        if code not in code_order:
            code_order.append(code)
    output_headers = [line for line in headers if line]
    if add_header:
        output_headers.append("; 加入当前symbo.txt全部快符；保留综合主表中的稀疏候选序号")
    output = output_headers + ([""] if output_headers else [])
    grouped: dict[str, list[tuple[int, str]]] = {code: [] for code in code_order}
    for (code, rank), text in occupied.items():
        grouped[code].append((rank, text))
    for code in code_order:
        for rank, text in sorted(grouped[code]):
            output.append(f"{code},{rank}={text}")
    return output


def add_short_words(lines: list[str], short_words: list[tuple[str, int, str]]) -> list[str]:
    headers = [line for line in lines if not line or line.startswith(";")]
    data = [line for line in lines if line and not line.startswith(";")]
    existing: dict[str, list[tuple[int, str]]] = OrderedDict()
    for raw in data:
        left, text = raw.split("=", 1)
        code, rank_text = left.rsplit(",", 1)
        existing.setdefault(code, []).append((int(rank_text), text))
    reserved: dict[str, dict[int, str]] = OrderedDict()
    for code, rank, text in short_words:
        old = reserved.setdefault(code, {}).get(rank)
        if old is not None and old != text:
            raise ValueError(f"简词自身位置冲突：{code},{rank}={text}；原值={old}")
        reserved[code][rank] = text
    code_order = list(existing) + [code for code in reserved if code not in existing]
    output = [line for line in headers if line]
    if output:
        output.append("")
    for code in code_order:
        bucket = dict(reserved.get(code, {}))
        for original_rank, text in existing.get(code, []):
            rank = original_rank
            while rank in bucket and bucket[rank] != text:
                rank += 1
            bucket[rank] = text
        output.extend(f"{code},{rank}={text}" for rank, text in sorted(bucket.items()))
    return output


def write(path: Path, lines: list[str]) -> None:
    path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", type=Path, required=True)
    parser.add_argument("--combined", type=Path, required=True)
    parser.add_argument("--quick", type=Path, required=True)
    parser.add_argument("--short-words", type=Path, required=True)
    parser.add_argument("--extension-characters", type=Path)
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output_dir = args.output_dir or args.release_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    single_rows = read_plain(args.single)
    combined_rows = read_plain(args.combined)
    quick = read_quick(args.quick)
    short_words = read_short_words(args.short_words)
    extension_characters = read_extension_characters(args.extension_characters) if args.extension_characters else []
    extension_set = {text for _code, _rank, text in extension_characters}
    # 扩展字已经属于两张主表。挂接时暂时抽出，再按显式候选位放回，
    # 避免与表外的简词、快符候选位冲突。
    single_slots = slots([row for row in single_rows if row[0] not in extension_set])
    short_pairs = {(text, code) for code, _rank, text in short_words}
    combined_slots = slots([row for row in combined_rows if row[0] not in extension_set])
    single_headers = [
        "; 夜莺码v0.8.5综合字词主表派生搜狗无二字词挂接版",
        "; 写入单字与夜莺简词；省略普通全码词并保留其候选序号空位，供搜狗自带词库联想",
    ]
    # 搜狗挂接文件本身只写单字，但候选位必须继承综合字词主表：
    # 若综合表首位是词，单字需从 ,2 开始，让搜狗自带词库占据联想首位。
    single_sogou = render_no_two_words(combined_slots, single_headers, short_pairs)
    single_sogou = add_short_words(single_sogou, extension_characters)
    # 搜狗完整词库版受十万条上限约束，仍不写简词；简词只进入无二字词版。
    # 先按完整主表确定候选序号，再省略词；不可预先过滤简词，否则单字会错误前移。
    combined_sogou = render_sogou(combined_slots, [], True)
    single_quick = add_quick(single_sogou, quick, True)
    combined_quick = add_quick(combined_sogou, quick, False)
    outputs = {
        "夜莺码v0.8.5无二字词版_搜狗.txt": single_sogou,
        "夜莺码v0.8.5无二字词版_搜狗_含快符.txt": single_quick,
        "夜莺码v0.8.5挂接字词版_搜狗词库.txt": combined_sogou,
        "夜莺码v0.8.5挂接字词版_搜狗词库_含快符.txt": combined_quick,
    }
    for name, lines in outputs.items():
        write(output_dir / name, lines)
    manifest_path = args.release_dir / "发布清单.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for legacy_name in ("夜莺码v0.8.5单字版_搜狗.txt", "夜莺码v0.8.5单字版_搜狗_含快符.txt"):
        manifest["outputs"].pop(legacy_name, None)
    manifest["derived_from_masters"] = {
        str(args.single.resolve()): sha256(args.single),
        str(args.combined.resolve()): sha256(args.combined),
        str(args.quick.resolve()): sha256(args.quick),
        str(args.short_words.resolve()): sha256(args.short_words),
    }
    for name in list(manifest["outputs"]):
        output_path = args.release_dir / name
        if output_path.exists():
            manifest["outputs"][name] = sha256(output_path)
    for name in outputs:
        output_path = output_dir / name
        manifest["outputs"][output_path.relative_to(args.release_dir).as_posix()] = sha256(output_path)
    try:
        short_word_name = args.short_words.resolve().relative_to(args.release_dir.resolve()).as_posix()
    except ValueError:
        short_word_name = None
    if short_word_name:
        manifest["outputs"][short_word_name] = sha256(args.short_words)
    extension_name = None
    if args.extension_characters:
        manifest["derived_from_masters"][str(args.extension_characters.resolve())] = sha256(args.extension_characters)
        try:
            extension_name = args.extension_characters.resolve().relative_to(args.release_dir.resolve()).as_posix()
        except ValueError:
            extension_name = None
    if extension_name:
        manifest["outputs"][extension_name] = sha256(args.extension_characters)
    else:
        manifest["outputs"].pop("夜莺码v0.8.5扩展字表.tsv", None)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"single_master={len(single_rows)} combined_master={len(combined_rows)} "
        f"short_words={len(short_words)} extension_characters={len(extension_characters)} quick={len(quick)} "
        + " ".join(f"{name}={sum(bool(x) and not x.startswith(';') for x in lines)}" for name, lines in outputs.items())
    )


if __name__ == "__main__":
    main()
