#!/usr/bin/env python3
"""比较“皮→毛m”与“毛→皮e”两种锨定方向的重码影响。"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "releases" / "v0.8.5"
BASE_SPLITS = ROOT / "work" / "重开工程" / "02_规范拆分" / "最终规范拆分表_待核验.tsv"
EXT_SPLITS = ROOT / "work" / "夜莺0.85" / "10_扩展字Chai实验" / "20260830_034806+1000" / "扩展字全码_结构候选.tsv"
OUT = ROOT / "work" / "夜莺0.85" / "14_毛皮锨定方向评估"


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def entries(path: Path) -> list[tuple[str, str]]:
    result = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if raw and not raw.startswith(";"):
            result.append(tuple(raw.split("\t")[:2]))
    return result


def metric(items: list[tuple[str, str]]) -> dict[str, int]:
    slots: dict[str, set[str]] = defaultdict(set)
    for text, code in items:
        slots[code].add(text)
    return {
        "collision_slots": sum(len(v) > 1 for v in slots.values()),
        "extra_candidates": sum(max(0, len(v) - 1) for v in slots.values()),
        "maximum_candidates": max(map(len, slots.values()), default=0),
    }


def move(singles, splits, irrational, root, key):
    output, changed = [], []
    for char, code in singles:
        new = code
        if (char, code) not in irrational and len(code) in (3, 4) and char in splits:
            head, tail = splits[char]
            chars = list(code)
            if head == root:
                chars[2] = key
            if len(code) == 4 and tail == root:
                chars[3] = key
            new = "".join(chars)
        output.append((char, new))
        if new != code:
            changed.append((char, code, new, "简码" if len(code) < 4 else "全码"))
    return output, changed


def family_review_rows(singles, moved, splits, core, root):
    family_chars = {char for char, (head, tail) in splits.items() if root in {head, tail}}
    current_by_char: dict[str, list[str]] = defaultdict(list)
    first_index: dict[str, int] = {}
    for index, (char, code) in enumerate(singles):
        if char in family_chars:
            current_by_char[char].append(code)
            first_index.setdefault(char, index)
    shortest = {char: min(map(len, codes)) for char, codes in current_by_char.items()}
    rows = []
    for (char, old), (_, new) in zip(singles, moved):
        if char not in family_chars:
            continue
        head, tail = splits[char]
        rows.append((char, old, new, "是" if old != new else "否",
                     "二简" if len(old) == 2 else "三简" if len(old) == 3 else "全码",
                     "核心8105" if char in core else "扩展字", head, tail))
    rows.sort(key=lambda row: (
        row[5] != "核心8105", shortest[row[0]], first_index[row[0]], len(row[1]), row[1]
    ))
    return rows


def main() -> None:
    base_rows = read_tsv(BASE_SPLITS)
    splits = {r["汉字"]: (r["编码首根"], r["编码末根"]) for r in base_rows}
    core = set(splits)
    for r in read_tsv(EXT_SPLITS):
        splits[r["汉字"]] = (r["编码首根"], r["编码末根"])
    tables = RELEASE / "01_正式码表"
    irrational = {(r["字"], r["新增码"]) for r in read_tsv(tables / "夜莺码v0.8.5无理码表.tsv")}
    singles = entries(tables / "夜莺码v0.8.5单字版.txt")
    combined = entries(tables / "夜莺0.8.5字词表.txt")
    words = [(t, c) for t, c in combined if len(t) > 1]
    short_words = [(r["词"], r["简码"]) for r in read_tsv(tables / "夜莺码v0.8.5简词表.tsv")]
    core_before = [(t, c) for t, c in singles if t in core]

    scenarios = {"皮→毛m": ("皮", "m"), "毛→皮e": ("毛", "e")}
    report = {"baseline": {}, "scenarios": {}}
    layer_sources = {
        "核心简码": lambda rows: [(t, c) for t, c in rows if t in core and len(c) < 4],
        "核心全码": lambda rows: [(t, c) for t, c in rows if t in core and len(c) == 4],
        "核心单字": lambda rows: [(t, c) for t, c in rows if t in core],
        "核心单字+普通词": lambda rows: [(t, c) for t, c in rows if t in core] + words,
        "核心单字+全部词": lambda rows: [(t, c) for t, c in rows if t in core] + words + short_words,
        "发布全部单字": lambda rows: rows,
        "发布全表": lambda rows: rows + words + short_words,
    }
    for layer, select in layer_sources.items():
        report["baseline"][layer] = metric(select(singles))
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (root, key) in scenarios.items():
        moved, changed = move(singles, splits, irrational, root, key)
        data = {"root": root, "target_key": key, "changed_entries": len(changed),
                "changed_short": sum(x[3] == "简码" for x in changed),
                "changed_full": sum(x[3] == "全码" for x in changed), "layers": {}}
        for layer, select in layer_sources.items():
            before = report["baseline"][layer]; after = metric(select(moved))
            data["layers"][layer] = {"after": after, "delta": {k: after[k] - before[k] for k in before}}
        report["scenarios"][name] = data
        detail = [(*row, "核心8105" if row[0] in core else "扩展字", *splits[row[0]]) for row in changed]
        with (OUT / f"{name}_受影响码.tsv").open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f, delimiter="\t", lineterminator="\n")
            w.writerow(("字", "原码", "新码", "层级", "范围", "首根", "末根")); w.writerows(detail)
        review = family_review_rows(singles, moved, splits, core, root)
        family_lines = [f"# {name}家族逐字审查表", "",
                        "排序：核心8105在前，扩展字在后；核心字内按二简、三简、仅全码排序。同字的全部入口相邻。", "",
                        f"- 家族字数：{len({x[0] for x in review})}",
                        f"- 展示全部入口：{len(review)}；其中实际改码{len(detail)}条", "",
                        "|字|现码|新码|变化|入口|范围|首根|末根|", "|---|---|---|---|---|---|---|---|"]
        family_lines.extend(f"|{char}|`{old}`|`{new}`|{changed_flag}|{level}|{scope}|{head}|{tail}|"
                            for char, old, new, changed_flag, level, scope, head, tail in review)
        (OUT / f"{name}_家族全量变化.md").write_text("\n".join(family_lines) + "\n", encoding="utf-8")
    (OUT / "比较结果.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 毛皮锨定方向比较", "", "|方案|受影响简码|受影响全码|核心简码额外候选Δ|核心全码额外候选Δ|核心单字Δ|加普通词Δ|加全部词Δ|", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, data in report["scenarios"].items():
        d = data["layers"]
        lines.append(f"|{name}|{data['changed_short']}|{data['changed_full']}|{d['核心简码']['delta']['extra_candidates']:+d}|{d['核心全码']['delta']['extra_candidates']:+d}|{d['核心单字']['delta']['extra_candidates']:+d}|{d['核心单字+普通词']['delta']['extra_candidates']:+d}|{d['核心单字+全部词']['delta']['extra_candidates']:+d}|")
    (OUT / "比较报告.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report["scenarios"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
