#!/usr/bin/env python3
"""生成冠军基础词表，并报告词重与单字全码—词码撞车。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def write_tsv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--single-table", type=Path, required=True)
    ap.add_argument("--two-words", type=Path, required=True)
    ap.add_argument("--four-words", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)

    audit = load_tsv(args.audit)
    two, four = load_tsv(args.two_words), load_tsv(args.four_words)
    if len(two) != 60000 or len(four) != 17860:
        raise ValueError(f"词库行数异常：二字{len(two)}，四字{len(four)}")
    if any(len(x["word"]) != 2 or len(x["code"]) != 4 for x in two):
        raise ValueError("二字词含非二字或非四码项")
    if any(len(x["word"]) < 4 or len(x["code"]) != 4 for x in four):
        raise ValueError("四字词含短词或非四码项")

    words = []
    for rank, row in enumerate(two, 1):
        words.append({"word": row["word"], "code": row["code"], "kind": "二字", "rank": rank,
                      "score": row.get("score", ""), "corpus_count": ""})
    for rank, row in enumerate(four, 1):
        words.append({"word": row["word"], "code": row["code"], "kind": "四字及以上", "rank": rank,
                      "score": "", "corpus_count": row.get("corpus_total_count", "")})
    if len({x["word"] for x in words}) != len(words):
        raise ValueError("基础词库词条重复")

    by_code: dict[str, list[dict]] = defaultdict(list)
    for item in words: by_code[item["code"]].append(item)
    collision_groups = {code: items for code, items in by_code.items() if len(items) > 1}
    word_collision_rows = []
    for code, items in sorted(collision_groups.items()):
        ordered = sorted(items, key=lambda x: (x["kind"] != "二字", x["rank"], x["word"]))
        word_collision_rows.append({"code": code, "count": len(items),
                                    "extra_candidates": len(items) - 1,
                                    "two_words": " ".join(x["word"] for x in ordered if x["kind"] == "二字"),
                                    "four_words": " ".join(x["word"] for x in ordered if x["kind"] != "二字")})

    chars_by_full: dict[str, list[dict]] = defaultdict(list)
    for row in audit:
        if len(row["字"]) != 1 or len(row["全码"]) != 4:
            raise ValueError("审计表含异常字或全码")
        chars_by_full[row["全码"]].append(row)
    char_word_rows = []
    for code in sorted(set(chars_by_full) & set(by_code)):
        items = by_code[code]
        tw = sorted((x for x in items if x["kind"] == "二字"), key=lambda x: x["rank"])
        fw = sorted((x for x in items if x["kind"] != "二字"), key=lambda x: x["rank"])
        for char in chars_by_full[code]:
            all_same_initial = all(item["word"].startswith(char["字"]) for item in items)
            direct = char["实际码"] == char["全码"]
            if not direct:
                status = "简码已避开"
            elif all_same_initial:
                status = "同首字可保留"
            else:
                status = "直接撞车待审"
            char_word_rows.append({"code": code, "char": char["字"], "pinyin": char["拼音"],
                "char_rank": int(char["原始行号"]), "char_frequency": int(char["频率"]), "two_count": len(tw), "four_count": len(fw),
                "actual_code": char["实际码"], "status": status,
                "two_top_rank": tw[0]["rank"] if tw else "", "four_top_rank": fw[0]["rank"] if fw else "",
                "two_words": " ".join(x["word"] for x in tw), "four_words": " ".join(x["word"] for x in fw)})
    status_order = {"直接撞车待审": 0, "同首字可保留": 1, "简码已避开": 2}
    char_word_rows.sort(key=lambda x: (status_order[x["status"]], x["two_top_rank"] or 10**9,
                                       x["four_top_rank"] or 10**9, -x["char_frequency"]))

    word_table = args.output / "基础词码表_77860.txt"
    word_table.write_text("\n".join(f"{x['word']}\t{x['code']}" for x in words) + "\n", encoding="utf-8")
    combined = args.output / "冠军无简词综合字词试验表.txt"
    actual_pairs = {(row["字"], row["实际码"]) for row in audit}
    full_pairs = {(row["字"], row["全码"]) for row in audit if row["实际码"] != row["全码"]}
    single_rows = []
    for line_no, line in enumerate(args.single_table.read_text(encoding="utf-8-sig").splitlines(), 1):
        fields = line.split("\t")
        if len(fields) != 2 or len(fields[0]) != 1:
            raise ValueError(f"单字表第{line_no}行异常")
        char, code = fields
        if (char, code) in actual_pairs:
            source = "实际码"
        elif (char, code) in full_pairs:
            source = "保留全码"
        else:
            raise ValueError(f"单字表第{line_no}行无法由审计表解释：{char} {code}")
        single_rows.append((char, code, source))
    missing_full = sorted(full_pairs - {(char, code) for char, code, _ in single_rows})
    if missing_full:
        raise ValueError(f"修正版单字表仍缺保留全码：{missing_full[:10]}")

    # 全局分段写入即可保证每个码位都是“原实际字 → 词 → 保留全码”；
    # 同字同码既是实际码又是其它读音的保留全码时，按实际码处理且只写一次。
    actual_lines = [f"{char}\t{code}" for char, code, source in single_rows if source == "实际码"]
    retained_lines = [f"{char}\t{code}" for char, code, source in single_rows if source == "保留全码"]
    word_lines = [f"{x['word']}\t{x['code']}" for x in words]
    combined.write_text("\n".join(actual_lines + word_lines + retained_lines) + "\n", encoding="utf-8")

    # 门禁：过滤新增内容后，实际单字序列必须与输入表中的实际序列逐项一致。
    if [(char, code) for char, code, source in single_rows if source == "实际码"] != [
            tuple(line.split("\t")) for line in actual_lines]:
        raise ValueError("原实际单字候选序列发生变化")
    write_tsv(args.output / "词词重码明细.tsv", word_collision_rows,
              ["code", "count", "extra_candidates", "two_words", "four_words"])
    write_tsv(args.output / "字词相撞明细.tsv", char_word_rows,
              ["code", "char", "pinyin", "char_rank", "char_frequency", "actual_code", "status", "two_count", "four_count",
               "two_top_rank", "four_top_rank", "two_words", "four_words"])

    tier_data = {}
    for top in (20000, 30000, 60000):
        subset = two[:top]
        slots: dict[str, int] = defaultdict(int)
        for item in subset: slots[item["code"]] += 1
        tier_data[str(top)] = {"words": len(subset), "unique_slots": len(slots),
            "collision_slots": sum(n > 1 for n in slots.values()),
            "extra_candidates": sum(n - 1 for n in slots.values() if n > 1),
            "maximum_slot_size": max(slots.values())}
    report = {"schema_version": 1, "inputs": {str(p.resolve()): sha256(p) for p in
              (args.audit, args.single_table, args.two_words, args.four_words)},
              "words": len(words), "two_words": len(two), "four_words": len(four),
              "unique_word_slots": len(by_code), "word_collision_slots": len(collision_groups),
              "word_extra_candidates": sum(len(x) - 1 for x in collision_groups.values()),
              "maximum_word_slot_size": max(map(len, by_code.values())),
              "char_word_collision_identities": len(char_word_rows),
              "char_word_collision_codes": len(set(x["code"] for x in char_word_rows)),
              "direct_review_identities": sum(x["status"] == "直接撞车待审" for x in char_word_rows),
              "same_initial_identities": sum(x["status"] == "同首字可保留" for x in char_word_rows),
              "protected_by_short_identities": sum(x["status"] == "简码已避开" for x in char_word_rows),
              "actual_single_entries": len(actual_lines),
              "retained_full_entries": len(retained_lines),
              "direct_review_top20000": sum(bool(x["status"] == "直接撞车待审" and x["two_top_rank"] != "" and x["two_top_rank"] <= 20000) for x in char_word_rows),
              "direct_review_top30000": sum(bool(x["status"] == "直接撞车待审" and x["two_top_rank"] != "" and x["two_top_rank"] <= 30000) for x in char_word_rows),
              "front3527_direct_top20000": sum(bool(x["status"] == "直接撞车待审" and x["char_rank"] <= 3527 and x["two_top_rank"] != "" and x["two_top_rank"] <= 20000) for x in char_word_rows),
              "front3527_direct_top30000": sum(bool(x["status"] == "直接撞车待审" and x["char_rank"] <= 3527 and x["two_top_rank"] != "" and x["two_top_rank"] <= 30000) for x in char_word_rows),
              "two_word_tiers": tier_data,
              "outputs": {str(p.name): sha256(p) for p in (word_table, combined,
                  args.output / "词词重码明细.tsv", args.output / "字词相撞明细.tsv")}}
    (args.output / "词性能.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 冠军C19基础词性能", "", "## 规模", "",
        f"- 二字词：{len(two)}；四字及以上：{len(four)}；合计：{len(words)}。",
        f"- 唯一码位：{len(by_code)}；词重码位：{len(collision_groups)}；额外候选：{report['word_extra_candidates']}；最大候选：{report['maximum_word_slot_size']}。",
        f"- 实际单字条目：{len(actual_lines)}；出简后保留全码：{len(retained_lines)}（统一位于词后）。",
        f"- 单字全码—词码相撞：{report['char_word_collision_codes']}个码位、{len(char_word_rows)}个读音身份。", "",
        f"- 其中简码已避开{report['protected_by_short_identities']}；同首字可保留{report['same_initial_identities']}；直接待审{report['direct_review_identities']}。",
        f"- 直接待审中撞前20000二字词{report['direct_review_top20000']}项，撞前30000二字词{report['direct_review_top30000']}项。", "",
        f"- 收窄到前3527字：撞前20000词{report['front3527_direct_top20000']}项；撞前30000词{report['front3527_direct_top30000']}项。", "",
        "## 二字词分层", "", "|前N词|唯一码位|重码位|额外候选|最大候选|", "|---:|---:|---:|---:|---:|"]
    for top, data in tier_data.items():
        lines.append(f"|{top}|{data['unique_slots']}|{data['collision_slots']}|{data['extra_candidates']}|{data['maximum_slot_size']}|")
    lines += ["", "## 高频字词相撞（按本报告排序前30）", "",
              "|码|字|音|字排名|字频|二字词最高排名|四字词最高排名|二字词|四字词|", "|---|---|---|---:|---:|---:|---:|---|---|"]
    focused = [row for row in char_word_rows if row["status"] == "直接撞车待审" and row["char_rank"] <= 3527 and ((row["two_top_rank"] != "" and row["two_top_rank"] <= 30000) or row["four_top_rank"] != "")]
    focused.sort(key=lambda x: (x["two_top_rank"] or 10**9, x["four_top_rank"] or 10**9, x["char_rank"]))
    for x in focused:
        lines.append(f"|{x['code']}|{x['char']}|{x['pinyin']}|{x['char_rank']}|{x['char_frequency']}|{x['two_top_rank']}|{x['four_top_rank']}|{x['two_words']}|{x['four_words']}|")
    lines += ["", "注意：综合表已自动应用“出简让全”：原实际单字在前、词居中、保留全码在后；无简码单字与词仍暂按单字优先，等待逐项审查。它不是发布表。", ""]
    (args.output / "词性能报告.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
