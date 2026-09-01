# -*- coding: utf-8 -*-
"""Build a fresh toneless character-reading frequency table from Chai dictionary."""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import audit_manual_split_propagation as common


PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
CURRENT = PROJECT / "02_规范拆分" / "最终规范拆分表_待核验.tsv"
DICTIONARY = ROOT / "repos" / "webchai" / "packages" / "hanzi-chai" / "src" / "data" / "dictionary.txt"
OUT_DIR = PROJECT / "03_字音频率"
OUT_TSV = OUT_DIR / "全新字音频率表_待核验.tsv"
MANIFEST = OUT_DIR / "全新字音频率表_生成清单.json"
README = OUT_DIR / "全新字音频率表_说明.md"
TONE = re.compile(r"[1-5]$")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with CURRENT.open("r", encoding="utf-8-sig", newline="") as f:
        structure_rows = list(csv.DictReader(f, delimiter="\t"))
    order = [x["汉字"] for x in structure_rows]
    if len(order) != 8105 or len(set(order)) != 8105:
        raise ValueError("current canonical table is not 8105 unique glyphs")
    rank = {char: i for i, char in enumerate(order)}
    charset = set(order)

    grouped: dict[tuple[str, str], list[tuple[str, int]]] = defaultdict(list)
    raw_single_rows = 0
    for line_no, line in enumerate(DICTIONARY.read_text(encoding="utf-8").splitlines(), 1):
        fields = line.split("\t")
        if len(fields) < 3:
            continue
        char, pinyin, frequency_text = fields[:3]
        if len(char) != 1 or char not in charset:
            continue
        if not pinyin:
            raise ValueError(f"target glyph has empty pinyin at dictionary line {line_no}: {char}")
        try:
            frequency = int(frequency_text)
        except ValueError as exc:
            raise ValueError(f"invalid frequency at dictionary line {line_no}") from exc
        if frequency < 0:
            raise ValueError(f"negative frequency at dictionary line {line_no}")
        toneless = TONE.sub("", pinyin)
        if not toneless:
            raise ValueError(f"empty toneless pinyin at dictionary line {line_no}: {char}")
        grouped[(char, toneless)].append((pinyin, frequency))
        raw_single_rows += 1

    covered = {char for char, _ in grouped}
    if covered != charset:
        raise ValueError(f"dictionary coverage mismatch: missing={sorted(charset-covered)} extra={sorted(covered-charset)}")

    rows = []
    for (char, pinyin), sources in grouped.items():
        frequency = sum(x[1] for x in sources)
        rows.append({
            "汉字": char,
            "拼音": pinyin,
            "频率": frequency,
            "来源行数": len(sources),
            "来源明细": " | ".join(f"{sound}:{freq}" for sound, freq in sources),
        })
    rows.sort(key=lambda x: (-int(x["频率"]), rank[x["汉字"]], x["拼音"]))
    keys = {(x["汉字"], x["拼音"]) for x in rows}
    if len(rows) != len(keys):
        raise ValueError("duplicate character-reading key after aggregation")
    if sum(int(x["来源行数"]) for x in rows) != raw_single_rows:
        raise ValueError("source row aggregation mismatch")

    fields = ["汉字", "拼音", "频率", "来源行数", "来源明细"]
    with OUT_TSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    with OUT_TSV.open("r", encoding="utf-8-sig", newline="") as f:
        check = list(csv.DictReader(f, delimiter="\t"))
    if len(check) != len(rows) or {(x["汉字"], x["拼音"]) for x in check} != keys:
        raise ValueError("written table validation failed")

    now = datetime.now(ZoneInfo("Australia/Sydney")).isoformat(timespec="minutes")
    distribution: dict[int, int] = defaultdict(int)
    by_char: dict[str, int] = defaultdict(int)
    for row in rows:
        by_char[row["汉字"]] += 1
    for count in by_char.values():
        distribution[count] += 1
    manifest = {
        "generated_at": now,
        "status": "fresh_reading_table_pending_validation",
        "upstream_corpus_provenance": "unverified_beyond_pinned_chai_dictionary",
        "glyphs": len(by_char),
        "dictionary_single_char_rows": raw_single_rows,
        "toneless_character_reading_items": len(rows),
        "merged_tone_only_rows": raw_single_rows - len(rows),
        "zero_frequency_items": sum(int(x["频率"]) == 0 for x in rows),
        "items_per_glyph_distribution": dict(sorted(distribution.items())),
        "inputs": {str(p.relative_to(ROOT)): common.sha256(p) for p in [CURRENT, DICTIONARY, Path(__file__)]},
        "outputs": {str(OUT_TSV.relative_to(ROOT)): common.sha256(OUT_TSV)},
        "historical_assets_read": [],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    README.write_text(
        "# 全新字音频率表\n\n"
        f"- 生成时间：{now}\n"
        "- 起点：当前正式8105＋固定Chai dictionary.txt。\n"
        "- 未读取任何历史readings或8455元素表。\n"
        f"- 原始单字读音行：{raw_single_rows}。\n"
        f"- 去调后的字音项：{len(rows)}。\n"
        f"- 合并的纯声调差异行：{raw_single_rows-len(rows)}。\n"
        f"- 零频字音项：{manifest['zero_frequency_items']}。\n"
        "- Chai词典文件及哈希已固定，但其更上游语料出处尚未证实。\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
