#!/usr/bin/env python3
"""模拟黄部件末根由㐅/交(n)修正为八(a)的重码影响，不修改正式数据。"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "releases" / "v0.9.1"
TABLES = RELEASE / "01_正式码表"
CORE_SPLITS = ROOT / "work" / "重开工程" / "02_规范拆分" / "最终规范拆分表_待核验.tsv"
EXT_SPLITS = ROOT / "work" / "夜莺0.85" / "10_扩展字Chai实验" / "20260830_034806+1000" / "扩展字规范拆分_候选.tsv"
SINGLE = TABLES / "夜莺码v0.9.1单字版.txt"
COMBINED = TABLES / "夜莺0.9.1字词表.txt"
OUT = ROOT / "work" / "夜莺0.85" / "16_黄末根八影响评估"


def read_splits(path: Path) -> dict[str, list[str]]:
    result = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        fields = raw.split("\t")
        if number == 1 and fields[0] in {"字", "汉字", "character"}:
            continue
        if len(fields) >= 2:
            result[fields[0]] = [part.strip() for part in fields[1].split("＋")]
    return result


def read_table(path: Path) -> list[tuple[str, str]]:
    return [tuple(raw.split("\t")) for raw in path.read_text(encoding="utf-8-sig").splitlines() if raw]


def buckets(rows: list[tuple[str, str]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for text, code in rows:
        result[code].append(text)
    return result


def extras(data: dict[str, list[str]]) -> int:
    return sum(max(0, len(items) - 1) for items in data.values())


def main() -> None:
    core = read_splits(CORE_SPLITS)
    extension = read_splits(EXT_SPLITS)
    pattern = ["龷", "一", "日", "㐅"]

    def affected(parts: list[str]) -> bool:
        return len(parts) >= 4 and parts[-1] == "㐅" and any(parts[i:i + 4] == pattern for i in range(len(parts) - 3))

    scopes = {char: "核心8105" for char, parts in core.items() if affected(parts)}
    scopes.update({char: "扩展字" for char, parts in extension.items() if affected(parts)})
    split_map = {**extension, **core}
    single_rows = read_table(SINGLE)
    combined_rows = read_table(COMBINED)

    changes = []
    change_pairs = set()
    for char, code in single_rows:
        if char in scopes and len(code) == 4 and code.endswith("n"):
            new_code = code[:-1] + "a"
            changes.append({"字": char, "范围": scopes[char], "原码": code, "新码": new_code,
                            "拆分": " ＋ ".join(split_map[char])})
            change_pairs.add((char, code, new_code))

    def simulate(rows: list[tuple[str, str]]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        before = buckets(rows)
        changed = {(char, old): new for char, old, new in change_pairs}
        after_rows = [(text, changed.get((text, code), code)) for text, code in rows]
        return before, buckets(after_rows)

    single_before, single_after = simulate(single_rows)
    combined_before, combined_after = simulate(combined_rows)
    changed_codes = sorted({row["原码"] for row in changes} | {row["新码"] for row in changes})
    detail = []
    for code in changed_codes:
        detail.append({
            "码位": code,
            "单字原候选": "、".join(single_before.get(code, [])),
            "单字新候选": "、".join(single_after.get(code, [])),
            "字词原候选": "、".join(combined_before.get(code, [])),
            "字词新候选": "、".join(combined_after.get(code, [])),
            "单字候选变化": len(single_after.get(code, [])) - len(single_before.get(code, [])),
            "字词候选变化": len(combined_after.get(code, [])) - len(combined_before.get(code, [])),
        })

    summary = {
        "affected_characters": len({row["字"] for row in changes}),
        "changed_full_code_entries": len(changes),
        "core_characters": len({row["字"] for row in changes if row["范围"] == "核心8105"}),
        "extension_characters": len({row["字"] for row in changes if row["范围"] == "扩展字"}),
        "single_extra_candidates_before": extras(single_before),
        "single_extra_candidates_after": extras(single_after),
        "single_extra_delta": extras(single_after) - extras(single_before),
        "combined_extra_candidates_before": extras(combined_before),
        "combined_extra_candidates_after": extras(combined_after),
        "combined_extra_delta": extras(combined_after) - extras(combined_before),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "全码变化.tsv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(changes[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(changes)
    with (OUT / "码位候选变化.tsv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(detail[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(detail)
    (OUT / "结果.json").write_text(json.dumps({"summary": summary, "changes": changes, "slots": detail}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 黄末根改八重码评估", "", "本报告仅模拟，不修改正式拆分或码表。", "",
             f"- 影响字数：{summary['affected_characters']}（核心{summary['core_characters']}，扩展{summary['extension_characters']}）",
             f"- 全码入口变化：{summary['changed_full_code_entries']}",
             f"- 单字表额外候选变化：{summary['single_extra_delta']:+d}",
             f"- 综合字词表额外候选变化：{summary['combined_extra_delta']:+d}", "", "## 核心字变化", "",
             "|字|原码|新码|", "|---|---|---|"]
    lines += [f"|{row['字']}|`{row['原码']}`|`{row['新码']}`|" for row in changes if row["范围"] == "核心8105"]
    lines += ["", "## 新码位候选", ""]
    for row in changes:
        if row["范围"] != "核心8105":
            continue
        slot = next(item for item in detail if item["码位"] == row["新码"])
        lines.append(f"- `{row['新码']}`：{slot['字词新候选'] or '空'}")
    (OUT / "比较报告.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
