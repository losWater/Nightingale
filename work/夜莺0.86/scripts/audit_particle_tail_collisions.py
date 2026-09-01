#!/usr/bin/env python3
"""按语法尾字读音审计缺失二字口语组合的夜莺码位冲突；不修改主表。"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

import yaml


TAIL_READINGS = {"了": "le", "着": "zhe", "过": "guo", "吗": "ma", "吧": "ba",
                 "呢": "ne", "啊": "a", "呀": "ya", "嘛": "ma", "呗": "bei"}


def load_identity_codes(elements_path: Path, layout_path: Path) -> tuple[dict[tuple[str, str], str], dict[str, set[str]]]:
    elements = yaml.safe_load(elements_path.read_text(encoding="utf-8"))
    mapping = yaml.safe_load(layout_path.read_text(encoding="utf-8"))["form"]["mapping"]
    identities: dict[tuple[str, str], str] = {}
    readings: dict[str, set[str]] = defaultdict(set)
    for row in elements:
        seq = row["元素序列"]
        if len(row["词"]) == 1 and len(seq) >= 2:
            code = mapping[seq[0]["element"]] + mapping[seq[1]["element"]]
            identities[(row["词"], row["拼音"])] = code
            readings[row["词"]].add(row["拼音"])
    return identities, readings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--missing-audit", type=Path, required=True)
    parser.add_argument("--combined", type=Path, required=True)
    parser.add_argument("--short-words", type=Path, required=True)
    parser.add_argument("--extension", type=Path, required=True)
    parser.add_argument("--elements", type=Path, required=True)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    with args.missing_audit.open("r", encoding="utf-8-sig", newline="") as stream:
        missing = [row for row in csv.DictReader(stream, delimiter="\t") if row["词"][1] in TAIL_READINGS]
    combined = []
    buckets: dict[str, list[str]] = defaultdict(list)
    for raw in args.combined.read_text(encoding="utf-8-sig").splitlines():
        text, code = raw.split("\t")
        combined.append((text, code)); buckets[code].append(text)
    with args.short_words.open("r", encoding="utf-8-sig", newline="") as stream:
        short_pairs = {(row["词"], row["简码"]) for row in csv.DictReader(stream, delimiter="\t")}
    with args.extension.open("r", encoding="utf-8-sig", newline="") as stream:
        extension = {row["字"] for row in csv.DictReader(stream, delimiter="\t")}
    identities, readings = load_identity_codes(args.elements, args.layout)

    rows = []
    for source in missing:
        word = source["词"]
        head, tail = word
        tail_reading = TAIL_READINGS[tail]
        head_options = sorted(readings.get(head, set()))
        codes = []
        for head_reading in head_options:
            if (head, head_reading) in identities and (tail, tail_reading) in identities:
                codes.append((head_reading, identities[(head, head_reading)] + identities[(tail, tail_reading)]))
        # 前字多音时保留所有合法码，交给人工按词义选音；单读音可以直接定码。
        for head_reading, code in codes or [("", "")]:
            existing = buckets.get(code, []) if code else []
            core = [x for x in existing if len(x) == 1 and x not in extension]
            ext = [x for x in existing if len(x) == 1 and x in extension]
            ordinary = [x for x in existing if len(x) > 1 and (x, code) not in short_pairs]
            shorts = [x for x in existing if (x, code) in short_pairs]
            collision = "空码" if code and not existing else "+".join(
                label for label, values in (("核心字", core), ("普通词", ordinary), ("简词", shorts), ("扩展字", ext)) if values
            ) or "无法定码"
            rows.append({
                "词": word, "尾字语法读音": tail_reading, "前字读音": head_reading,
                "前字是否多音": "是" if len(head_options) > 1 else "否", "建议码": code,
                "冲突类型": collision, "现有码位候选数": str(len(existing)),
                "预计追加候选位": str(len(existing) + 1) if code else "",
                "现有候选": "、".join(existing),
                "备注": "前字需按词义选音" if len(head_options) > 1 else "尾字按语法助词定音",
            })

    rows.sort(key=lambda r: (r["词"][1], r["词"], r["前字读音"]))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    for suffix, delimiter in (("tsv", "\t"), ("csv", ",")):
        with (args.output_dir / f"口语尾字缺词冲突审计.{suffix}").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, delimiter=delimiter)
            writer.writeheader(); writer.writerows(rows)

    unique_words = {r["词"] for r in rows}
    single_reading = [r for r in rows if r["前字是否多音"] == "否" and r["建议码"]]
    collision_counts = Counter(r["冲突类型"] for r in single_reading)
    tail_counts = Counter(r["词"][1] for r in rows)
    bad = next((r for r in rows if r["词"] == "坏了" and r["前字读音"] == "huai"), None)
    lines = ["# 口语尾字缺词冲突审计（未实装）", "",
             f"- 差异词：{len(unique_words):,} 个；展开前字多音后：{len(rows):,} 个词码候选；",
             f"- 前字唯一读音、可直接定码：{len(single_reading):,} 个；",
             *[f"- {tail}：{count:,} 个词码候选；" for tail, count in tail_counts.items()],
             "", "## 前字唯一读音词的冲突", "",
             *[f"- {kind}：{count:,} 个；" for kind, count in collision_counts.most_common()], ""]
    if bad:
        lines += ["## 坏了", "", f"- 建议码 `{bad['建议码']}`；{bad['冲突类型']}；预计候选位 {bad['预计追加候选位']}。", ""]
    lines += ["尾字读音按语法助词口径固定；前字多音词仍保留多套候选，未擅自选音。正式码表未修改。", ""]
    (args.output_dir / "口语尾字冲突摘要.md").write_text("\n".join(lines), encoding="utf-8")
    print({"words": len(unique_words), "expanded": len(rows), "single_reading": len(single_reading),
           "collisions": dict(collision_counts), "bad": bad})


if __name__ == "__main__":
    main()
