# -*- coding: utf-8 -*-
"""生成夜莺 0.7 单字向二字词让位的完整台账。"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import yaml

from build_v07_release import load_default_word_first_codes


BROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = BROOT / "work/v07_unlocked_audit/当前复审基线_卩y_讠m_媚无理"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", type=Path, default=DEFAULT_DIR / "code_应用全部谕旨_复核.txt")
    ap.add_argument("--elements", type=Path, default=DEFAULT_DIR / "elements.yaml")
    ap.add_argument("--output", type=Path, default=BROOT / "work/v07_unlocked_audit/夜莺0.7词位让位总表.md")
    args = ap.parse_args()

    rows = [line.split("\t") for line in args.code.read_text(encoding="utf-8").splitlines()]
    elements = yaml.safe_load(args.elements.read_text(encoding="utf-8"))
    manual = yaml.safe_load((BROOT / "work/简码资产.yaml").read_text(encoding="utf-8"))
    rules = yaml.safe_load((BROOT / "work/拆分规则.yaml").read_text(encoding="utf-8"))

    chars_by_code = defaultdict(list)
    for row, item in zip(rows, elements):
        rank = int(item.get("排序序号", 10**12)) + 1
        chars_by_code[str(row[1])].append((str(row[0]), rank, str(row[3])))

    words = {}
    with (BROOT / "work/lexicon/目标词库_四码位.tsv").open(
        encoding="utf-8-sig", newline=""
    ) as f:
        for row in csv.DictReader(f, delimiter="\t"):
            words[str(row["code"])] = row

    explicit = {str(code) for code in (manual.get("sogou_candidate_offsets") or {})}
    automatic = load_default_word_first_codes(rows, elements, manual)
    compensation = {
        str(code): str(char)
        for code, char in (manual.get("word_yield_three_secondaries") or {}).items()
    }
    extras = {str(code): str(char) for code, char in (manual.get("extra_codes") or {}).items()}

    mapping = rules.get("sequence_overrides") or {}
    alternate_main = {}
    # 当前两项顺取主码；源规则用码元保存，最终字母在本轮布局中固定。
    known_alternates = {"椅": "yiav", "怡": "yivk"}
    for code, char in extras.items():
        if char in mapping and char in known_alternates:
            alternate_main[(code, char)] = known_alternates[char]

    def word_text(code: str) -> tuple[str, str]:
        row = words.get(code, {})
        rank = row.get("two_top_rank", "")
        text = row.get("two_words", "")
        return str(rank), str(text).replace("|", "／")

    def char_text(code: str) -> str:
        parts = []
        for char, rank, short in sorted(chars_by_code.get(code, []), key=lambda x: x[1]):
            parts.append(f"{char}（{rank}）")
        return "、".join(parts) or "—"

    def escape_text(code: str) -> str:
        details = []
        for char, _, short in sorted(chars_by_code.get(code, []), key=lambda x: x[1]):
            if compensation.get(code) == char:
                details.append(f"{char}：`{code[:3]}` 三码二选")
            elif (code, char) in alternate_main:
                details.append(f"{char}：另有主码 `{alternate_main[(code, char)]}`")
            elif len(short) < len(code):
                details.append(f"{char}：已有简码 `{short}`")
            else:
                details.append(f"{char}：无额外三码候选")
        return "；".join(details) or "—"

    def table(codes: list[str]) -> list[str]:
        out = ["| 四码 | 让位单字（字频序） | 首选二字词 | 词频序 | 单字补偿／候选 |",
               "|---|---|---|---:|---|"]
        for code in codes:
            rank, text = word_text(code)
            out.append(
                f"| `{code}` | {char_text(code)} | {text or '—'} | {rank or '—'} | {escape_text(code)} |"
            )
        return out

    manual_codes = sorted(explicit)
    automatic_codes = sorted(automatic - explicit)
    lines = [
        "# 夜莺 0.7 词位让位总表",
        "",
        "## 口径",
        "",
        "- 人工让位：逐项裁决；普通纯单表以 `①` 占位，搜狗序号表将单字后移。",
        "- 自动让位：字频序 3762 以后，撞前 30000 二字词时默认词优先。",
        "- 四字简词不触发自动让位。",
        "- 自动让位字不补三码；只有人工登记项才可获得三码二选补偿。",
        "",
        f"## 人工让位（{len(manual_codes)} 个码位）",
        "",
        *table(manual_codes),
        "",
        f"## 自动让位且无人工补偿（{len(automatic_codes)} 个码位）",
        "",
        *table(automatic_codes),
        "",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"manual={len(manual_codes)} automatic={len(automatic_codes)} output={args.output}")


if __name__ == "__main__":
    main()
