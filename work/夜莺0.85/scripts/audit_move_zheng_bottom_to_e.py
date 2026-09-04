#!/usr/bin/env python3
"""评估把“争字底”从 q 移到 e（秉与其同键）对 0.9 发布主表的重码影响。"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "releases" / "v0.9"
OUT = ROOT / "work" / "夜莺0.85" / "13_争字底移e影响评估"
BASE_SPLITS = ROOT / "work" / "重开工程" / "02_规范拆分" / "最终规范拆分表_待核验.tsv"
EXT_SPLITS = ROOT / "work" / "夜莺0.85" / "10_扩展字Chai实验" / "20260830_034806+1000" / "扩展字全码_结构候选.tsv"


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def load_splits() -> tuple[dict[str, tuple[str, str]], set[str]]:
    result = {r["汉字"]: (r["编码首根"], r["编码末根"]) for r in read_tsv(BASE_SPLITS)}
    core = set(result)
    for r in read_tsv(EXT_SPLITS):
        result[r["汉字"]] = (r["编码首根"], r["编码末根"])
    return result, core


def entries(path: Path) -> list[tuple[str, str]]:
    rows = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line or line.startswith(";"):
            continue
        text, code = line.split("\t")[:2]
        rows.append((text, code))
    return rows


def metric(items: list[tuple[str, str]]) -> dict[str, int]:
    slots: dict[str, set[str]] = defaultdict(set)
    for text, code in items:
        slots[code].add(text)
    return {
        "entries": sum(map(len, slots.values())),
        "slots": len(slots),
        "collision_slots": sum(len(v) > 1 for v in slots.values()),
        "extra_candidates": sum(max(0, len(v) - 1) for v in slots.values()),
        "maximum_candidates": max(map(len, slots.values()), default=0),
    }


def main() -> None:
    splits, core_chars = load_splits()
    tables = RELEASE / "01_正式码表"
    irrational = {(r["字"], r["新增码"]) for r in read_tsv(tables / "夜莺码v0.9无理码表.tsv")}
    singles = entries(tables / "夜莺码v0.9单字版.txt")
    combined = entries(tables / "夜莺0.9字词表.txt")
    short_words = [(r["词"], r["简码"]) for r in read_tsv(tables / "夜莺码v0.9简词表.tsv")]
    words = [(t, c) for t, c in combined if len(t) > 1]

    changed = []
    moved_singles = []
    missing = set()
    for char, code in singles:
        new = code
        if (char, code) not in irrational and len(code) in (3, 4):
            if char not in splits:
                missing.add(char)
            else:
                head, tail = splits[char]
                chars = list(code)
                if head in {"争字底", "秉"}:
                    chars[2] = "e"
                if len(code) == 4 and tail in {"争字底", "秉"}:
                    chars[3] = "e"
                new = "".join(chars)
        moved_singles.append((char, new))
        if new != code:
            changed.append((char, code, new, "简码" if len(code) < 4 else "全码"))
    if missing:
        raise SystemExit(f"缺拆分：{sorted(missing)[:20]}")

    core_before = [(t, c) for t, c in singles if t in core_chars]
    core_after = [(t, c) for t, c in moved_singles if t in core_chars]
    layers = {
        "8105单字简码": ([(t, c) for t, c in core_before if len(c) < 4], [(t, c) for t, c in core_after if len(c) < 4]),
        "8105单字全码": ([(t, c) for t, c in core_before if len(c) == 4], [(t, c) for t, c in core_after if len(c) == 4]),
        "8105全部单字": (core_before, core_after),
        "8105单字+普通词": (core_before + words, core_after + words),
        "8105单字+普通词+简词": (core_before + words + short_words, core_after + words + short_words),
        "单字简码": ([(t, c) for t, c in singles if len(c) < 4], [(t, c) for t, c in moved_singles if len(c) < 4]),
        "单字全码": ([(t, c) for t, c in singles if len(c) == 4], [(t, c) for t, c in moved_singles if len(c) == 4]),
        "全部单字": (singles, moved_singles),
        "普通词": (words, words),
        "简词": (short_words, short_words),
        "单字+普通词": (singles + words, moved_singles + words),
        "单字+普通词+简词": (singles + words + short_words, moved_singles + words + short_words),
    }
    report = {"assumption": "争字底 q→e，秉作为独立主根同键锪e；无理码保持不变", "changed_entries": len(changed),
              "changed_short": sum(x[3] == "简码" for x in changed),
              "changed_full": sum(x[3] == "全码" for x in changed), "layers": {}}
    for name, (before_items, after_items) in layers.items():
        before, after = metric(before_items), metric(after_items)
        report["layers"][name] = {"before": before, "after": after,
                                  "delta": {k: after[k] - before[k] for k in before}}

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "评估结果.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (OUT / "受影响单字码.tsv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n"); w.writerow(("字", "原码", "新码", "层级")); w.writerows(changed)
    lines = ["# 争字底移至 e 键重码影响", "", f"- 受影响单字码条目：{len(changed)}（简码{report['changed_short']}，全码{report['changed_full']}）", "",
             "|层级|原重码位|新重码位|净变化|原额外候选|新额外候选|净变化|", "|---|---:|---:|---:|---:|---:|---:|"]
    for name, data in report["layers"].items():
        b, a, d = data["before"], data["after"], data["delta"]
        lines.append(f"|{name}|{b['collision_slots']}|{a['collision_slots']}|{d['collision_slots']:+d}|{b['extra_candidates']}|{a['extra_candidates']}|{d['extra_candidates']:+d}|")
    (OUT / "评估报告.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
