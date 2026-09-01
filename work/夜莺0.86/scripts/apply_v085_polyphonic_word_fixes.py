#!/usr/bin/env python3
"""应用高置信度多音词改码，并按基础词表顺序重排同码词候选。"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def read_plain(path: Path) -> list[tuple[str, str]]:
    return [tuple(line.split("\t")) for line in path.read_text(encoding="utf-8-sig").splitlines() if line]  # type: ignore[misc]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--combined", type=Path, required=True)
    parser.add_argument("--base-words", type=Path, required=True)
    parser.add_argument("--fixes", type=Path, required=True)
    parser.add_argument("--candidate-decisions", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    combined = read_plain(args.combined)
    base_words = read_plain(args.base_words)
    priority = {word: index for index, (word, _code) in enumerate(base_words)}
    with args.fixes.open("r", encoding="utf-8-sig", newline="") as handle:
        fixes = list(csv.DictReader(handle, delimiter="\t"))

    by_code: dict[str, list[str]] = defaultdict(list)
    for text, code in combined:
        by_code[code].append(text)
    source_pairs = {(text, code) for text, code in combined}
    fix_words = {row["词"] for row in fixes}
    if len(fix_words) != len(fixes):
        raise ValueError("纠错表存在重复词")
    for row in fixes:
        pair = (row["词"], row["当前码"])
        if pair not in source_pairs:
            raise ValueError(f"纠错源条目不存在：{pair}")
        by_code[row["当前码"]].remove(row["词"])

    incoming: dict[str, list[str]] = defaultdict(list)
    for row in fixes:
        incoming[row["建议码"]].append(row["词"])
    for code, words in incoming.items():
        bucket = by_code[code]
        for word in sorted(words, key=lambda item: priority[item]):
            insert_at = len(bucket)
            for index, existing in enumerate(bucket):
                if len(existing) > 1 and priority.get(existing, 10**9) > priority[word]:
                    insert_at = index
                    break
            bucket.insert(insert_at, word)

    if args.candidate_decisions:
        with args.candidate_decisions.open("r", encoding="utf-8-sig", newline="") as handle:
            decisions = list(csv.DictReader(handle, delimiter="\t"))
        for row in decisions:
            code = row["码"]
            expected = row["调整前"].split("、")
            replacement = row["调整后"].split("、")
            if by_code.get(code) != expected:
                raise ValueError(f"码位裁决源值不符：{code}，期望{expected}，实际{by_code.get(code)}")
            if sorted(expected) != sorted(replacement):
                raise ValueError(f"码位裁决候选集合变化：{code}")
            by_code[code] = replacement

    all_codes = sorted((code for code, items in by_code.items() if items), key=lambda code: (len(code), code))
    output_rows = [(text, code) for code in all_codes for text in by_code[code]]
    if len(output_rows) != len(combined):
        raise ValueError("应用纠错后总条目数不守恒")
    if len({(text, code) for text, code in output_rows}) != len(output_rows):
        raise ValueError("应用纠错后出现重复字词码对")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "夜莺码v0.8.5挂接字词版_多音词校正.txt"
    output.write_bytes(("\n".join(f"{text}\t{code}" for text, code in output_rows) + "\n").encode("utf-8"))
    audit = args.output_dir / "多音词改码应用审计.tsv"
    fields = ["词", "原码", "新码", "新候选位", "新码全部候选", "SUBTLEX拼音", "SUBTLEX词频", "状态"]
    with audit.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for row in fixes:
            bucket = by_code[row["建议码"]]
            writer.writerow({
                "词": row["词"], "原码": row["当前码"], "新码": row["建议码"],
                "新候选位": bucket.index(row["词"]) + 1, "新码全部候选": " ".join(bucket),
                "SUBTLEX拼音": row["SUBTLEX拼音"], "SUBTLEX词频": row["SUBTLEX词频"], "状态": "已应用",
            })
    print(
        f"fixes={len(fixes)} decisions={len(decisions) if args.candidate_decisions else 0} "
        f"entries={len(output_rows)} codes={len(all_codes)}"
    )


if __name__ == "__main__":
    main()
