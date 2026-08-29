# -*- coding: utf-8 -*-
"""Validate that regenerated v0.7 assets preserve the approved layout and decrees."""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from short_code_overrides import apply_overrides  # noqa: E402

BROOT = HERE.parent
BASE = BROOT.parent


def table(path: Path) -> dict[str, list[str]]:
    out = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        phrase, code = line.split("\t")
        out[code].append(phrase)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--release", type=Path, required=True)
    args = ap.parse_args()

    released_layout = yaml.safe_load(
        (args.release / "夜莺码v0.7键位布局.yaml").read_text(encoding="utf-8")
    )["form"]["mapping"]
    source_layout = yaml.safe_load(args.config.read_text(encoding="utf-8"))["form"]["mapping"]
    if released_layout != source_layout:
        raise AssertionError("发布键位布局与锁定配置不一致")

    rows = [line.split("\t") for line in (args.run / "code.txt").read_text(
        encoding="utf-8").splitlines()]
    apply_overrides(rows)  # 内含全码集合对冻结基线的硬门禁。
    pure = table(args.release / "夜莺码v0.7纯单版.txt")
    no_yield = table(args.release / "夜莺码v0.7纯单版_不让位.txt")
    mixed = table(args.release / "夜莺码v0.7字词版_无简词.txt")

    for char, full, _, short, *_ in rows:
        if char not in no_yield[full] or char not in pure[full]:
            raise AssertionError(f"全码未落实：{char} {full}")
        if short != full and (char not in no_yield[short] or char not in pure[short]):
            raise AssertionError(f"简码未落实：{char} {short}")

    expected = {
        "jmmv": "箭", "yigl": "裔", "jnf": "缴", "jnfe": "绞",
        "djm": "诞", "djmn": "耽", "vjbj": "粘", "jigd": "饥",
    }
    for code, char in expected.items():
        if not no_yield[code] or no_yield[code][0] != char:
            raise AssertionError(f"关键谕旨候选错误：{code} 应首选 {char}，实际 {no_yield[code][:3]}")

    manual = yaml.safe_load((BROOT / "work/简码资产.yaml").read_text(encoding="utf-8"))
    for code in (manual.get("sogou_candidate_offsets") or {}):
        if not pure[code] or pure[code][0] != "①":
            raise AssertionError(f"让位纯单表缺少唯一占位：{code}")
        if "①" in no_yield[code]:
            raise AssertionError(f"不让位纯单表混入占位：{code}")

    lexicon = []
    with (BROOT / "work/lexicon/二字词_精选60000.tsv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        lexicon = [(str(row["code"]), str(row["word"]))
                   for row in csv.DictReader(handle, delimiter="\t")]
    missing_words = [(code, word) for code, word in lexicon if word not in mixed[code]]
    if missing_words:
        raise AssertionError(f"综合表缺少精选二字词：{missing_words[:8]}")
    for code, word in (manual.get("word_first_overrides") or {}).items():
        if not mixed[str(code)] or mixed[str(code)][0] != str(word):
            raise AssertionError(f"指定词首选未落实：{code}={word}")

    print(f"layout_mapping={len(source_layout)} unchanged")
    print(f"code_rows={len(rows)} baseline_identity=pass")
    print(f"pure_entries={sum(map(len, pure.values()))}")
    print(f"no_yield_entries={sum(map(len, no_yield.values()))}")
    print(f"mixed_entries={sum(map(len, mixed.values()))} lexicon_words={len(lexicon)}")
    print("manual_decrees=pass word_yields=pass")


if __name__ == "__main__":
    main()
