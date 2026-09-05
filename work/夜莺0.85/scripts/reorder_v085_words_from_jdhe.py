#!/usr/bin/env python3
"""按简单鹤纯词库的词序重排夜莺0.9.1综合字词主表的四码普通词，并补入简单鹤二/三字词。

规则（只作用于四码位；一二三码位与快符一律不动）：
  1. 单字（核心字与扩展字）守住当前候选位；
  2. 人工裁决过的字词（字词裁决表“调整后关键候选”、实战问题机器参数表涉及的字词）守住当前候选位；
  3. 四码简词（简词表级别≥4）若简单鹤同码也收录，则随简单鹤词序；否则守住当前候选位；
  4. 其余普通词按简单鹤纯词库同码顺序依次填入空位；简单鹤有而夜莺没有的二字词、三字词按夜莺规则
     从单字音码重编后补入（多音字优先取与简单鹤码一致的读音，其次取多音词纠错建议，再次取主读音；
     简单鹤飞键因此自然消失）；夜莺有而简单鹤没有的词按原相对顺序排在简单鹤词之后。
默认只预演并输出摘要；--output-combined/--output-short-words 写到新路径；--in-place 才覆盖主表并留备份。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import OrderedDict, defaultdict
from datetime import datetime
from itertools import product
from pathlib import Path


def read_plain(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw:
            continue
        parts = raw.split("\t")
        if len(parts) != 2 or not parts[0] or not parts[1].isascii() or not parts[1].isalpha() or not parts[1].islower():
            raise ValueError(f"{path}:{line_number}: 非法主表行：{raw!r}")
        rows.append((parts[0], parts[1]))
    return rows


def read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return list(reader.fieldnames or []), list(reader)


def read_jdhe_words(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not raw:
            continue
        parts = raw.split("\t")
        if len(parts) != 2:
            raise ValueError(f"{path}:{line_number}: 简单鹤纯词库应为‘词<Tab>码’：{raw!r}")
        rows.append((parts[0], parts[1]))
    return rows


def word_code(readings: list[str]) -> str:
    """夜莺词码：二字 AaAbBaBb；三字 AaBaCaCb；四字以上 AaBaCaZa。"""
    if len(readings) == 2:
        return readings[0] + readings[1]
    if len(readings) == 3:
        return readings[0][0] + readings[1][0] + readings[2]
    return readings[0][0] + readings[1][0] + readings[2][0] + readings[-1][0]


def build_readings(single_rows: list[tuple[str, str]], readings_json: Path | None) -> dict[str, list[str]]:
    """字 -> 音码列表，主读音在前：优先 readings.json 的次序，其次单字主表中四码条目的出现顺序。"""
    readings: dict[str, list[str]] = {}
    if readings_json and readings_json.is_file():
        data = json.loads(readings_json.read_text(encoding="utf-8"))
        for character, entries in data.items():
            for _freq, code in entries:
                if len(code) == 4:
                    lst = readings.setdefault(character, [])
                    if code[:2] not in lst:
                        lst.append(code[:2])
    for character, code in single_rows:
        if len(code) == 4:
            lst = readings.setdefault(character, [])
            if code[:2] not in lst:
                lst.append(code[:2])
    return readings


def split_candidates(text: str) -> list[str]:
    return [part for part in text.replace("，", "、").split("、") if part]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--combined", type=Path, required=True, help="综合字词主表")
    parser.add_argument("--single", type=Path, required=True, help="单字主表（提供读音）")
    parser.add_argument("--short-words", type=Path, required=True, help="简词表.tsv")
    parser.add_argument("--extension-characters", type=Path, required=True, help="扩展字表.tsv")
    parser.add_argument("--jdhe-words", type=Path, required=True, help="简单鹤纯词库（词<Tab>码，同码顺序即排位）")
    parser.add_argument("--readings", type=Path, help="work/v08/assets/readings.json（主读音次序）")
    parser.add_argument("--word-decisions", type=Path, help="字词裁决.tsv（调整后关键候选守位）")
    parser.add_argument("--practice-ledger", type=Path, help="实战问题机器参数.tsv（涉及字词守位）")
    parser.add_argument("--word-code-fixes", type=Path, help="多音词纠错建议.tsv（词/当前码/建议码）")
    parser.add_argument("--quick-symbols", type=Path, help="symbo.txt：有快符的码位不新增词，避免撞快符候选位")
    parser.add_argument("--output-combined", type=Path, help="重排后的综合主表输出路径")
    parser.add_argument("--output-short-words", type=Path, help="更新候选位后的简词表输出路径")
    parser.add_argument("--summary", type=Path, help="变更摘要 JSON 输出路径")
    parser.add_argument("--detail", type=Path, help="逐码位变更明细 TSV 输出路径")
    parser.add_argument("--in-place", action="store_true", help="直接覆盖 --combined 与 --short-words（需 --backup-dir）")
    parser.add_argument("--backup-dir", type=Path, help="--in-place 时的备份目录")
    args = parser.parse_args()
    if args.in_place and not args.backup_dir:
        parser.error("--in-place 必须同时给出 --backup-dir")

    combined_rows = read_plain(args.combined)
    single_rows = read_plain(args.single)
    short_fields, short_rows = read_tsv(args.short_words)
    _ext_fields, ext_rows = read_tsv(args.extension_characters)
    jdhe_rows = read_jdhe_words(args.jdhe_words)
    readings = build_readings(single_rows, args.readings)

    fixes: dict[str, str] = {}
    if args.word_code_fixes and args.word_code_fixes.is_file():
        _f, fix_rows = read_tsv(args.word_code_fixes)
        for row in fix_rows:
            if row.get("词") and row.get("建议码"):
                fixes[row["词"]] = row["建议码"]

    anchored_words: set[str] = set()
    if args.word_decisions and args.word_decisions.is_file():
        _f, rows = read_tsv(args.word_decisions)
        for row in rows:
            for column in ("调整前关键候选", "调整后关键候选"):
                anchored_words.update(x for x in split_candidates(row.get(column, "")) if len(x) > 1)
    if args.practice_ledger and args.practice_ledger.is_file():
        _f, rows = read_tsv(args.practice_ledger)
        for row in rows:
            for column in ("原字词", "新字词"):
                value = (row.get(column) or "").strip()
                if len(value) > 1:
                    anchored_words.add(value)

    quick_codes: set[str] = set()
    if args.quick_symbols and args.quick_symbols.is_file():
        for raw in args.quick_symbols.read_text(encoding="utf-8-sig").splitlines():
            if raw and "=" in raw:
                quick_codes.add(raw.split("=", 1)[0].rsplit(",", 1)[0])

    chars = {text for text, _code in single_rows} | {row["字"] for row in ext_rows}
    short_pairs = {(row["词"], row["简码"]) for row in short_rows}

    buckets: OrderedDict[str, list[str]] = OrderedDict()
    for text, code in combined_rows:
        buckets.setdefault(code, []).append(text)
    master_codes: dict[str, list[str]] = defaultdict(list)
    for text, code in combined_rows:
        master_codes[text].append(code)

    # 简单鹤四码词 → 夜莺码位上的顺序流（词序即排位；改码的词垫在目标码位末尾）
    flow_native: dict[str, list[str]] = defaultdict(list)
    flow_moved: dict[str, list[str]] = defaultdict(list)
    stats = {"jdhe_rows": 0, "jdhe_skipped_unknown_char": 0, "jdhe_recoded": 0, "jdhe_new_words": 0,
             "jdhe_long_words_ignored": 0}
    recoded_examples: list[tuple[str, str, str]] = []
    for text, jcode in jdhe_rows:
        if len(jcode) != 4 or len(text) < 2:
            continue
        stats["jdhe_rows"] += 1
        if text in master_codes:
            codes = master_codes[text]
            code = jcode if jcode in codes else codes[0]
        else:
            if len(text) > 3:
                stats["jdhe_long_words_ignored"] += 1   # 四字以上属简词层，按“简词不变”不新增
                continue
            if any(ch not in readings for ch in text):
                stats["jdhe_skipped_unknown_char"] += 1
                continue
            combos = [word_code(list(c)) for c in product(*(readings[ch] for ch in text))]
            if jcode in combos:
                code = jcode
            elif fixes.get(text) in combos:
                code = fixes[text]
            else:
                code = combos[0]
            stats["jdhe_new_words"] += 1
        if code == jcode:
            flow_native[code].append(text)
        else:
            flow_moved[code].append(text)
            stats["jdhe_recoded"] += 1
            if len(recoded_examples) < 30:
                recoded_examples.append((text, jcode, code))

    def flowing_jdhe_words(code: str) -> list[str]:
        if code in quick_codes:
            return []
        seen: set[str] = set()
        out: list[str] = []
        for text in flow_native.get(code, []) + flow_moved.get(code, []):
            if text not in seen:
                seen.add(text)
                out.append(text)
        return out

    new_buckets: OrderedDict[str, list[str]] = OrderedDict()
    detail_rows: list[tuple[str, str, str]] = []
    changed_codes = added_words = 0
    for code, items in buckets.items():
        jd = flowing_jdhe_words(code) if len(code) == 4 else []
        if not jd:
            new_buckets[code] = list(items)
            continue
        jd_set = set(jd)
        anchored: dict[int, str] = {}
        for position, text in enumerate(items, 1):
            is_char = text in chars
            is_short = (text, code) in short_pairs
            if is_char or text in anchored_words or (is_short and text not in jd_set):
                anchored[position] = text
        leftover = [text for text in items if text not in anchored.values() and text not in jd_set]
        flow = [text for text in jd if text not in anchored.values()] + leftover
        merged: list[str] = []
        position, flow_index = 1, 0
        while flow_index < len(flow) or any(p >= position for p in anchored):
            if position in anchored:
                merged.append(anchored[position])
            elif flow_index < len(flow):
                merged.append(flow[flow_index])
                flow_index += 1
            position += 1
        assert sorted(merged) == sorted(set(merged)), f"{code}: 合并后出现重复候选"
        assert set(items) <= set(merged), f"{code}: 合并后丢失候选"
        new_buckets[code] = merged
        added_words += len(merged) - len(items)
        if merged != items:
            changed_codes += 1
            detail_rows.append((code, "、".join(items), "、".join(merged)))
    for code in sorted(flow_native.keys() | flow_moved.keys(), key=lambda c: (len(c), c)):   # 新码位按（长度, 字母序）追加，保证可复现
        if code not in new_buckets and len(code) == 4:
            new_buckets[code] = flowing_jdhe_words(code)
            added_words += len(new_buckets[code])
            changed_codes += 1
            detail_rows.append((code, "", "、".join(new_buckets[code])))

    # 单字（含扩展字）在主表中的位置必须原封不动；扩展字表的显式候选位由派生脚本另行套用
    before = {(text, code): p for code, items in buckets.items() for p, text in enumerate(items, 1) if text in chars}
    after = {(text, code): p for code, merged in new_buckets.items() for p, text in enumerate(merged, 1) if text in chars}
    drifted = [(k, before[k], after.get(k)) for k in before if before[k] != after.get(k)]
    if drifted:
        raise ValueError(f"单字候选位漂移 {len(drifted)} 处，例如：{drifted[:5]}")
    assert all((row["字"], row["码"]) in after for row in ext_rows), "扩展字在主表中缺失"

    output_rows = [(text, code) for code, merged in new_buckets.items() for text in merged]
    position_of = {(text, code): p for code, merged in new_buckets.items() for p, text in enumerate(merged, 1)}
    updated_short: list[dict[str, str]] = []
    short_changed = 0
    for row in short_rows:
        row = dict(row)
        key = (row["词"], row["简码"])
        if key in position_of and str(position_of[key]) != row["候选位"]:
            short_changed += 1
            row["候选位"] = str(position_of[key])
        updated_short.append(row)

    summary = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "inputs": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                   (args.combined, args.single, args.short_words, args.extension_characters, args.jdhe_words)},
        "combined_rows_before": len(combined_rows),
        "combined_rows_after": len(output_rows),
        "codes_changed": changed_codes,
        "words_added": added_words,
        "short_word_rank_updates": short_changed,
        "anchored_decision_words": len(anchored_words),
        "quick_symbol_codes_frozen": sorted(c for c in quick_codes if len(c) == 4),
        "jdhe": stats,
        "recoded_examples": recoded_examples,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.detail:
        args.detail.parent.mkdir(parents=True, exist_ok=True)
        args.detail.write_text("码\t调整前\t调整后\n" + "".join(f"{c}\t{a}\t{b}\n" for c, a, b in detail_rows),
                               encoding="utf-8")

    combined_bytes = ("\n".join(f"{text}\t{code}" for text, code in output_rows) + "\n").encode("utf-8")
    short_lines = ["\t".join(short_fields)] + ["\t".join(row[f] for f in short_fields) for row in updated_short]
    short_bytes = ("\n".join(short_lines) + "\n").encode("utf-8")
    if args.in_place:
        args.backup_dir.mkdir(parents=True, exist_ok=True)
        for src in (args.combined, args.short_words):
            shutil.copy2(src, args.backup_dir / src.name)
        args.combined.write_bytes(combined_bytes)
        args.short_words.write_bytes(short_bytes)
        print(f"已原地更新：{args.combined} / {args.short_words}；备份于 {args.backup_dir}")
    else:
        if args.output_combined:
            args.output_combined.parent.mkdir(parents=True, exist_ok=True)
            args.output_combined.write_bytes(combined_bytes)
        if args.output_short_words:
            args.output_short_words.parent.mkdir(parents=True, exist_ok=True)
            args.output_short_words.write_bytes(short_bytes)
        if not (args.output_combined or args.output_short_words):
            print("预演模式：未写入任何码表（用 --output-* 或 --in-place 落盘）")


if __name__ == "__main__":
    main()
