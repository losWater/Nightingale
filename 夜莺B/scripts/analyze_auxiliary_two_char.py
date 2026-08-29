#!/usr/bin/env python3
"""计算“五码定二字”：四码同音词追加首字或尾字首型后的离散能力。"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
DEFAULT_LEXICON = BASE / "work" / "lexicon" / "二字词_精选60000.tsv"
DEFAULT_OUT = BASE / "work" / "auxiliary_code"


def read_code_table(path: Path) -> dict[tuple[str, str], str]:
    result: dict[tuple[str, str], str] = {}
    fallback: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        if len(fields) < 2 or len(fields[0]) != 1 or len(fields[1]) < 3:
            continue
        char, code = fields[0], fields[1]
        fallback.setdefault(char, code[2])
        result.setdefault((char, code[:2]), code[2])
    for char, key in fallback.items():
        result.setdefault((char, ""), key)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("code_table", type=Path)
    parser.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    shapes = read_code_table(args.code_table)
    rows = list(csv.DictReader(args.lexicon.open(encoding="utf-8-sig"), delimiter="\t"))
    records = []
    missing = []
    for rank, row in enumerate(rows, 1):
        word, base = row["word"], row["code"]
        if len(word) != 2 or len(base) != 4:
            continue
        first = shapes.get((word[0], base[:2]), shapes.get((word[0], "")))
        second = shapes.get((word[1], base[2:]), shapes.get((word[1], "")))
        if first is None or second is None:
            missing.append({"rank": rank, "word": word, "code": base})
            continue
        records.append({
            "rank": rank,
            "word": word,
            "code": base,
            "score": float(row["score"]),
            "first_shape": first,
            "second_shape": second,
        })

    groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        groups[record["code"]].append(record)

    ambiguous = [r for items in groups.values() if len(items) > 1 for r in items]
    total_weight = sum(r["score"] for r in ambiguous)
    stats = Counter()
    weighted = Counter()
    unresolved = []
    for code, items in groups.items():
        if len(items) <= 1:
            continue
        first_counts = Counter(r["first_shape"] for r in items)
        second_counts = Counter(r["second_shape"] for r in items)
        # 智能输入法仍负责排序；辅助码只筛选。因此按词频证据（score、全局词序）
        # 计算筛选后的候选名次，比强求整个大词库绝对唯一更贴近日用。
        first_buckets: dict[str, list[dict]] = defaultdict(list)
        second_buckets: dict[str, list[dict]] = defaultdict(list)
        for record in items:
            first_buckets[record["first_shape"]].append(record)
            second_buckets[record["second_shape"]].append(record)
        for bucket in list(first_buckets.values()) + list(second_buckets.values()):
            bucket.sort(key=lambda r: (-r["score"], r["rank"], r["word"]))
        first_ranks = {r["word"]: rank for bucket in first_buckets.values()
                       for rank, r in enumerate(bucket, 1)}
        second_ranks = {r["word"]: rank for bucket in second_buckets.values()
                        for rank, r in enumerate(bucket, 1)}
        for record in items:
            first_size = first_counts[record["first_shape"]]
            second_size = second_counts[record["second_shape"]]
            best_size = min(first_size, second_size)
            first_unique = first_size == 1
            second_unique = second_size == 1
            determined = best_size == 1
            first_rank = first_ranks[record["word"]]
            second_rank = second_ranks[record["word"]]
            best_rank = min(first_rank, second_rank)
            stats["ambiguous"] += 1
            stats["first"] += first_unique
            stats["second"] += second_unique
            stats["either"] += determined
            stats["burden"] += best_size - 1
            stats["first_choice"] += best_rank == 1
            stats["rank_burden"] += best_rank - 1
            for name, value in (("first", first_unique), ("second", second_unique), ("either", determined)):
                if value:
                    weighted[name] += record["score"]
            weighted["burden"] += record["score"] * (best_size - 1)
            weighted["first_choice"] += record["score"] * (best_rank == 1)
            weighted["rank_burden"] += record["score"] * (best_rank - 1)
            if not determined:
                unresolved.append({**record, "first_size": first_size, "second_size": second_size,
                                   "first_rank": first_rank, "second_rank": second_rank,
                                   "best_rank": best_rank, "group_size": len(items),
                                   "group_words": " ".join(x["word"] for x in items)})

    unresolved.sort(key=lambda r: (r["rank"], -r["score"], r["word"]))
    args.output.mkdir(parents=True, exist_ok=True)
    asset = {
        "code_table": str(args.code_table.resolve()),
        "lexicon": str(args.lexicon.resolve()),
        "word_count": len(records),
        "ambiguous_word_count": stats["ambiguous"],
        "records": records,
    }
    (args.output / "五码定二字资产.json").write_text(json.dumps(asset, ensure_ascii=False), encoding="utf-8")
    fields = ["rank", "word", "code", "score", "first_shape", "second_shape",
              "first_size", "second_size", "first_rank", "second_rank", "best_rank",
              "group_size", "group_words"]
    with (args.output / "五码仍重明细.tsv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(unresolved)

    percentage = lambda value, total: 100 * value / total if total else 0
    report = [
        "# 五码定二字基准报告", "",
        f"- 二字词：{len(records):,}",
        f"- 四码同音组：{sum(len(x) > 1 for x in groups.values()):,}",
        f"- 位于四码同音组的词：{stats['ambiguous']:,}",
        f"- 辅首字可定：{stats['first']:,}（{percentage(stats['first'], stats['ambiguous']):.2f}%）",
        f"- 辅尾字可定：{stats['second']:,}（{percentage(stats['second'], stats['ambiguous']):.2f}%）",
        f"- 首尾任选可定：{stats['either']:,}（{percentage(stats['either'], stats['ambiguous']):.2f}%）",
        f"- 加权首尾任选可定率：{percentage(weighted['either'], total_weight):.2f}%",
        f"- 五码仍重：{stats['ambiguous'] - stats['either']:,}",
        f"- 未定候选负担：{stats['burden']:,}；加权负担：{weighted['burden']:.4f}",
        f"- 辅码后回到首选：{stats['first_choice']:,}（{percentage(stats['first_choice'], stats['ambiguous']):.2f}%）",
        f"- 加权辅码首选率：{percentage(weighted['first_choice'], total_weight):.2f}%",
        f"- 辅码选重负担：{stats['rank_burden']:,}；加权负担：{weighted['rank_burden']:.4f}",
        f"- 缺少首型：{len(missing):,}", "",
        "## 高频五码仍重", "",
    ]
    report.extend(
        f"- {r['word']}（{r['code']}；首辅 {r['first_shape']}×{r['first_size']}；"
        f"尾辅 {r['second_shape']}×{r['second_size']}）：{r['group_words']}"
        for r in unresolved[:100]
    )
    (args.output / "五码定二字报告.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report[:13]))


if __name__ == "__main__":
    main()
