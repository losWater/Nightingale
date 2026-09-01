#!/usr/bin/env python3
"""比较卵族并入卩键与卩族并入卵键的全表重码影响；只分析。"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from compare_mao_pi_anchor_directions import read_tsv, entries, metric, move, family_review_rows


ROOT = Path(__file__).resolve().parents[3]
RELEASE = ROOT / "releases" / "v0.8.5"
BASE_SPLITS = ROOT / "work" / "重开工程" / "02_规范拆分" / "最终规范拆分表_待核验.tsv"
EXT_SPLITS = ROOT / "work" / "夜莺0.85" / "10_扩展字Chai实验" / "20260830_034806+1000" / "扩展字全码_结构候选.tsv"
OUT = ROOT / "work" / "夜莺0.85" / "15_卵卩合并方向评估"


def buckets(items: list[tuple[str, str]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for text, code in items:
        result[code].add(text)
    return result


def collision_type(items: set[str], core: set[str], extension: set[str], short_pairs: set[tuple[str, str]], code: str) -> str:
    labels = []
    if any(len(x) == 1 and x in core for x in items): labels.append("核心字")
    if any(len(x) == 1 and x in extension for x in items): labels.append("扩展字")
    if any(len(x) > 1 and (x, code) in short_pairs for x in items): labels.append("简词")
    if any(len(x) > 1 and (x, code) not in short_pairs for x in items): labels.append("普通词")
    return "+".join(labels) or "空码"


def main() -> None:
    base_rows = read_tsv(BASE_SPLITS)
    splits = {r["汉字"]: (r["编码首根"], r["编码末根"]) for r in base_rows}
    core = set(splits)
    ext_rows = read_tsv(EXT_SPLITS)
    for row in ext_rows:
        splits[row["汉字"]] = (row["编码首根"], row["编码末根"])
    extension = set(splits) - core
    tables = RELEASE / "01_正式码表"
    irrational = {(r["字"], r["新增码"]) for r in read_tsv(tables / "夜莺码v0.8.5无理码表.tsv")}
    singles = entries(tables / "夜莺码v0.8.5单字版.txt")
    combined = entries(tables / "夜莺0.8.5字词表.txt")
    short_pairs = {(r["词"], r["简码"]) for r in read_tsv(tables / "夜莺码v0.8.5简词表.tsv")}
    all_words = [(t, c) for t, c in combined if len(t) > 1]

    layers = {
        "核心简码": lambda rows: [(t, c) for t, c in rows if t in core and len(c) < 4],
        "核心全码": lambda rows: [(t, c) for t, c in rows if t in core and len(c) == 4],
        "核心单字": lambda rows: [(t, c) for t, c in rows if t in core],
        "核心单字+全部词": lambda rows: [(t, c) for t, c in rows if t in core] + all_words,
        "发布全部单字": lambda rows: rows,
        "发布全表": lambda rows: rows + all_words,
    }
    baseline = {name: metric(select(singles)) for name, select in layers.items()}
    base_full = buckets(singles + all_words)
    scenarios = {"卵族j→卩p": ("卵", "p"), "卩族p→卵j": ("卩", "j")}
    report = {"baseline": baseline, "scenarios": {}}
    OUT.mkdir(parents=True, exist_ok=True)

    for name, (root, key) in scenarios.items():
        moved, changed = move(singles, splits, irrational, root, key)
        after_full = buckets(moved + all_words)
        affected_codes = {old for _char, old, _new, _level in changed} | {new for _char, _old, new, _level in changed}
        detail_rows = []
        new_collisions = 0
        relieved_collisions = 0
        for code in sorted(affected_codes):
            before, after = base_full.get(code, set()), after_full.get(code, set())
            before_extra, after_extra = max(0, len(before) - 1), max(0, len(after) - 1)
            delta = after_extra - before_extra
            if delta > 0: new_collisions += delta
            if delta < 0: relieved_collisions -= delta
            detail_rows.append((code, "、".join(sorted(before)), "、".join(sorted(after)),
                                len(before), len(after), delta,
                                collision_type(before, core, extension, short_pairs, code),
                                collision_type(after, core, extension, short_pairs, code)))
        data = {"root": root, "target_key": key, "changed_entries": len(changed),
                "changed_short": sum(x[3] == "简码" for x in changed),
                "changed_full": sum(x[3] == "全码" for x in changed),
                "new_extra_candidates_on_affected_codes": new_collisions,
                "relieved_extra_candidates_on_affected_codes": relieved_collisions,
                "layers": {}}
        for layer, select in layers.items():
            after_metric = metric(select(moved))
            data["layers"][layer] = {"after": after_metric,
                "delta": {k: after_metric[k] - baseline[layer][k] for k in baseline[layer]}}
        report["scenarios"][name] = data

        with (OUT / f"{name}_受影响码.tsv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
            writer.writerow(("字", "原码", "新码", "层级", "范围", "首根", "末根"))
            writer.writerows((*row, "核心8105" if row[0] in core else "扩展字", *splits[row[0]]) for row in changed)
        with (OUT / f"{name}_冲突码位明细.tsv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
            writer.writerow(("码位", "调整前候选", "调整后候选", "前数量", "后数量", "额外候选变化", "前类型", "后类型"))
            writer.writerows(detail_rows)
        review = family_review_rows(singles, moved, splits, core, root)
        with (OUT / f"{name}_家族全量变化.tsv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
            writer.writerow(("字", "现码", "新码", "变化", "入口", "范围", "首根", "末根")); writer.writerows(review)

    (OUT / "比较结果.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 卵族与卩族合并方向比较（未实装）", "",
             "|方案|改简码|改全码|核心简码额外候选Δ|核心全码额外候选Δ|核心单字Δ|核心字+全部词Δ|发布全表Δ|",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, data in report["scenarios"].items():
        layer = data["layers"]
        lines.append(f"|{name}|{data['changed_short']}|{data['changed_full']}|"
                     f"{layer['核心简码']['delta']['extra_candidates']:+d}|{layer['核心全码']['delta']['extra_candidates']:+d}|"
                     f"{layer['核心单字']['delta']['extra_candidates']:+d}|{layer['核心单字+全部词']['delta']['extra_candidates']:+d}|"
                     f"{layer['发布全表']['delta']['extra_candidates']:+d}|")
    lines += ["", "全部明细均为模拟结果；根集和正式码表没有修改。", ""]
    (OUT / "比较报告.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report["scenarios"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
