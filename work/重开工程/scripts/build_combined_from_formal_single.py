#!/usr/bin/env python3
"""以正式普通单字表为唯一事实源，生成无简词综合字词审查表。"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_single(path: Path) -> tuple[dict[str, list[str]], list[tuple[str, str]]]:
    slots: dict[str, list[str]] = defaultdict(list)
    rows: list[tuple[str, str]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        fields = line.split("\t")
        if len(fields) != 2 or len(fields[0]) != 1 or not 1 <= len(fields[1]) <= 4:
            raise ValueError(f"正式单字表第{line_no}行异常")
        char, code = fields
        if char in slots[code]:
            raise ValueError(f"正式单字表同码同字重复：{code} {char}")
        slots[code].append(char); rows.append((char, code))
    return dict(slots), rows


def read_identity_layers(path: Path) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    required = {"字", "全码", "实际码"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("身份审计表缺少字、全码或实际码列")
    actual: set[tuple[str, str]] = set()
    retained: set[tuple[str, str]] = set()
    for row in rows:
        char, full, code = row["字"], row["全码"], row["实际码"]
        actual.add((char, code))
        if full != code:
            retained.add((char, full))
    return actual, retained


def read_layer_overrides(path: Path) -> dict[tuple[str, str], str]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    required = {"字", "码", "层级", "来源"}
    if not rows or set(rows[0]) != required:
        raise ValueError("人工路径层级表列异常")
    result: dict[tuple[str, str], str] = {}
    for row in rows:
        pair = (row["字"], row["码"])
        if pair in result or row["层级"] not in {"实际单字", "保留全码"}:
            raise ValueError(f"人工路径层级异常：{row}")
        result[pair] = row["层级"]
    return result


def read_words(path: Path, expected: int, kind: str) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        source = list(csv.DictReader(stream, delimiter="\t"))
    if len(source) != expected:
        raise ValueError(f"{kind}词数异常：期望{expected}，实际{len(source)}")
    result = []
    for rank, row in enumerate(source, 1):
        word, code = row.get("word", ""), row.get("code", "")
        if (kind == "二字" and len(word) != 2) or (kind == "四字及以上" and len(word) < 4):
            raise ValueError(f"{kind}第{rank}行词长异常：{word}")
        if len(code) != 4:
            raise ValueError(f"{kind}第{rank}行编码异常：{code}")
        result.append({"word": word, "code": code, "kind": kind, "rank": rank})
    return result


def write_tsv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--single-table", type=Path, required=True)
    ap.add_argument("--identity-audit", type=Path, required=True)
    ap.add_argument("--layer-overrides", type=Path, required=True)
    ap.add_argument("--two-words", type=Path, required=True)
    ap.add_argument("--four-words", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise ValueError("输出目录必须不存在")

    single_slots, single_rows = read_single(args.single_table)
    two = read_words(args.two_words, 60000, "二字")
    four = read_words(args.four_words, 17860, "四字及以上")
    words = two + four
    if len({str(x["word"]) for x in words}) != len(words):
        raise ValueError("两个基础词库中存在重复词条")

    identity_actual, identity_retained = read_identity_layers(args.identity_audit)
    layer_overrides = read_layer_overrides(args.layer_overrides)
    actual: dict[str, list[str]] = defaultdict(list)
    retained: dict[str, list[str]] = defaultdict(list)
    for code, chars in single_slots.items():
        for char in chars:
            pair = (char, code)
            layer = layer_overrides.get(pair)
            if layer is None:
                if pair in identity_actual:
                    layer = "实际单字"
                elif pair in identity_retained:
                    layer = "保留全码"
                else:
                    raise ValueError(f"正式表字码对无法追溯身份或人工来源：{char} {code}")
            (actual if layer == "实际单字" else retained)[code].append(char)
    if ("尺", "iiii") not in identity_actual or "尺" not in actual.get("iiii", []):
        raise ValueError("多音字回归失败：尺/chi@iiii未归为实际单字")
    if ("尉", "yuiy") not in identity_actual or "尉" not in actual.get("yuiy", []):
        raise ValueError("多音字回归失败：尉/yu@yuiy未归为实际单字")
    word_slots: dict[str, list[str]] = defaultdict(list)
    word_meta: dict[str, list[dict[str, object]]] = defaultdict(list)
    for item in words:
        code, word = str(item["code"]), str(item["word"])
        word_slots[code].append(word); word_meta[code].append(item)

    all_codes = sorted(set(actual) | set(word_slots) | set(retained), key=lambda x: (len(x), x))
    # 只能用get读取。defaultdict的下标读取会把不存在的码位写回集合，污染后续碰撞统计。
    combined = {}
    for code in all_codes:
        code_words = word_slots.get(code, [])
        combined[code] = (actual.get(code, []) + code_words[:1] + retained.get(code, [])
                          + code_words[1:])
    args.output.mkdir(parents=True)
    plain = args.output / "夜莺0.8_正式单字基线_无简词综合字词审查表.txt"
    sogou = args.output / "夜莺0.8_正式单字基线_无简词综合字词审查表_搜狗.txt"
    word_table = args.output / "基础词码表_77860.txt"
    plain.write_text("\n".join(f"{item}\t{code}" for code in all_codes for item in combined[code]) + "\n", encoding="utf-8")
    word_table.write_text("\n".join(f"{x['word']}\t{x['code']}" for x in words) + "\n", encoding="utf-8")
    sogou_lines = ["; 夜莺0.8 正式单字基线＋基础词审查表", "; 无777简词；实际单字→词→出简保留全码", ""]
    sogou_lines += [f"{code},{i}={item}" for code in all_codes for i, item in enumerate(combined[code], 1)]
    sogou.write_text("\n".join(sogou_lines) + "\n", encoding="utf-8")

    # 门禁：逐码验证三层和原单字层内顺序。
    for code in all_codes:
        code_words = word_slots.get(code, [])
        expected = (actual.get(code, []) + code_words[:1] + retained.get(code, [])
                    + code_words[1:])
        if combined[code] != expected:
            raise ValueError(f"分层顺序异常：{code}")
        original = single_slots.get(code, [])
        expected_actual = [char for char in original if char in actual.get(code, [])]
        expected_retained = [char for char in original if char in retained.get(code, [])]
        if actual.get(code, []) != expected_actual or retained.get(code, []) != expected_retained:
            raise ValueError(f"单字分层内部顺序发生变化：{code}")
    if sum(map(len, actual.values())) + sum(map(len, retained.values())) != len(single_rows):
        raise ValueError("单字条目数不守恒")
    if sum(map(len, word_slots.values())) != 77860:
        raise ValueError("词条目数不守恒")

    parsed: dict[str, list[str]] = defaultdict(list)
    for line in sogou.read_text(encoding="utf-8-sig").splitlines():
        if not line or line.startswith(";"):
            continue
        left, value = line.split("=", 1); code, pos = left.rsplit(",", 1)
        if int(pos) != len(parsed[code]) + 1:
            raise ValueError(f"搜狗候选序号不连续：{code}")
        parsed[code].append(value)
    if dict(parsed) != combined:
        raise ValueError("普通表与搜狗表反读不一致")

    word_collision_rows = []
    for code, items in word_meta.items():
        if len(items) > 1:
            word_collision_rows.append({"code": code, "count": len(items),
                "two_words": " ".join(str(x["word"]) for x in items if x["kind"] == "二字"),
                "four_words": " ".join(str(x["word"]) for x in items if x["kind"] != "二字")})
    word_collision_rows.sort(key=lambda x: x["code"])
    char_word_rows = []
    for code in sorted(set(single_slots) & set(word_slots)):
        tw = [x for x in word_meta[code] if x["kind"] == "二字"]
        fw = [x for x in word_meta[code] if x["kind"] != "二字"]
        for char in single_slots[code]:
            layer = "保留全码" if char in retained.get(code, []) else "实际单字"
            char_word_rows.append({"code": code, "char": char, "layer": layer,
                "status": "简码已自动让词" if layer == "保留全码" else "直接撞车待审",
                "two_top_rank": tw[0]["rank"] if tw else "", "four_top_rank": fw[0]["rank"] if fw else "",
                "two_words": " ".join(str(x["word"]) for x in tw),
                "four_words": " ".join(str(x["word"]) for x in fw)})
    char_word_rows.sort(key=lambda x: (x["status"] != "直接撞车待审", x["two_top_rank"] or 10**9,
                                       x["four_top_rank"] or 10**9, x["code"], x["char"]))
    write_tsv(args.output / "词词重码明细.tsv", word_collision_rows,
              ["code", "count", "two_words", "four_words"])
    write_tsv(args.output / "字词相撞明细.tsv", char_word_rows,
              ["code", "char", "layer", "status", "two_top_rank", "four_top_rank", "two_words", "four_words"])

    report = {"schema_version": 1, "status": "pass", "rule": "实际单字→首词→出简保留全码→其余词",
        "inputs": {str(p.resolve()): sha256(p) for p in (args.single_table, args.identity_audit, args.layer_overrides, args.two_words, args.four_words)},
        "single_entries": len(single_rows), "identity_actual_pairs": len(identity_actual),
        "actual_single_entries": sum(map(len, actual.values())),
        "retained_full_entries": sum(map(len, retained.values())),
        "words": len(words), "two_words": len(two), "four_words": len(four),
        "result_entries": sum(map(len, combined.values())), "result_slots": len(combined),
        "char_word_collision_codes": len(set(single_slots) & set(word_slots)),
        "direct_review_entries": sum(x["status"] == "直接撞车待审" for x in char_word_rows),
        "auto_yield_entries": sum(x["status"] == "简码已自动让词" for x in char_word_rows),
        "word_collision_slots": len(word_collision_rows),
        "outputs": {p.name: sha256(p) for p in (plain, sogou, word_table,
            args.output / "词词重码明细.tsv", args.output / "字词相撞明细.tsv")}}
    (args.output / "生成验证报告.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = ["# 正式单字基线无简词综合字词表", "",
        f"- 状态：{report['status']}", f"- 单字条目：{report['single_entries']}（实际{report['actual_single_entries']}，保留全码{report['retained_full_entries']}）",
        f"- 基础词：{report['words']}（二字{report['two_words']}，四字及以上{report['four_words']}）",
        f"- 字词相撞码位：{report['char_word_collision_codes']}；待审单字条目：{report['direct_review_entries']}；已自动让词：{report['auto_yield_entries']}",
        "", "生成规则：正式单字表是唯一单字事实源；有任意简码的字，其全部四码入口只让首词，随后排在其余词之前。"]
    (args.output / "生成摘要.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
