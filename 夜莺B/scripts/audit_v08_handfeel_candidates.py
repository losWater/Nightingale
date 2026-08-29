#!/usr/bin/env python3
"""展开0.8候选的简码跨排贡献与按键热力；只读，不修改码表。"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import yaml


ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm")
FINGERS = {
    **dict(zip("qaz", ("L5",) * 3)), **dict(zip("wsx", ("L4",) * 3)),
    **dict(zip("edc", ("L3",) * 3)), **dict(zip("rfvtgb", ("L2",) * 6)),
    **dict(zip("yuhjnm", ("R2",) * 6)), **dict(zip("ik", ("R3",) * 2)),
    **dict(zip("ol", ("R4",) * 2)), **dict(zip("p", ("R5",))),
}
ROW = {key: i for i, row in enumerate(ROWS) for key in row}
CHAI_LAYOUT = (
    "trewq", "gf dsa".replace(" ", ""), "bvcxz",
    "yuiop", "hjkl", "nm",
)
COL = {key: i for row in CHAI_LAYOUT for i, key in enumerate(row)}


def chai_pairs() -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    """按libchai objectives/metric.rs的同指跨排定义生成集合。"""
    large, small = set(), set()
    keys = "".join(ROWS)
    for a in keys:
        for b in keys:
            if FINGERS[a] != FINGERS[b]:
                continue
            delta = abs(ROW[a] - ROW[b])
            if delta >= 2:
                large.add((a, b))
            elif delta == 1 or abs(COL[a] - COL[b]) == 1:
                small.add((a, b))
    return large, small


def load_codes(path: Path, elements: list[dict]) -> list[tuple[str, str, int]]:
    rows = [line.split("\t") for line in path.read_text(encoding="utf-8").splitlines()]
    if len(rows) != len(elements):
        raise ValueError(f"{path}: code/elements行数不一致")
    result = []
    for item, row in zip(elements, rows):
        char = str(item["词"])
        if len(row) < 4 or row[0] != char:
            raise ValueError(f"{path}: code/elements错位：{char}/{row[:1]}")
        result.append((char, row[3], int(item.get("频率", 0))))
    # libchai在编码前按显式排序序号（若任一对象提供）或频率降序重排对象；
    # code.txt仍按资产原始顺序输出，因此审计分层时必须复现内部顺序。
    if any(item.get("排序序号") is not None for item in elements):
        indexed = list(enumerate(zip(elements, result)))
        indexed.sort(key=lambda x: (
            x[1][0].get("排序序号", 2**63 - 1)
            if x[1][0].get("排序序号") is not None else 2**63 - 1,
            x[0],
        ))
        return [record for _, (_, record) in indexed]
    return sorted(result, key=lambda x: -x[2])


def audit(records, top: int, bad_pairs: set[tuple[str, str]]):
    total = 0
    chars, pairs = Counter(), Counter()
    for char, code, freq in records[:top]:
        for a, b in zip(code, code[1:]):
            total += freq
            if (a, b) in bad_pairs:
                chars[f"{char}({code})"] += freq
                pairs[a + b] += freq
    return total, chars, pairs


def heat(records, top: int):
    all_keys, third_keys = Counter(), Counter()
    total = third_total = 0
    for _, code, freq in records[:top]:
        for key in code:
            all_keys[key] += freq
            total += freq
        if len(code) >= 3:
            third_keys[code[2]] += freq
            third_total += freq
    return total, all_keys, third_total, third_keys


def pct(value: int, total: int) -> str:
    return f"{value / total * 100:.2f}%" if total else "0"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--elements", type=Path, required=True)
    ap.add_argument("--candidate", action="append", required=True,
                    help="名称=code.txt，可重复")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    elements = yaml.safe_load(args.elements.read_text(encoding="utf-8"))
    large, small = chai_pairs()
    candidates = []
    for spec in args.candidate:
        name, sep, raw_path = spec.partition("=")
        if not sep:
            raise ValueError("--candidate格式必须为名称=路径")
        candidates.append((name, load_codes(Path(raw_path), elements)))

    out = ["# 0.8候选简码手感与热力审计", "",
           "按单字频率加权；跨排集合与libchai定义一致。热力同时报告实际简码全部键和可变的第三键。", ""]
    for name, records in candidates:
        out += [f"## {name}", ""]
        for top in (300, 500, 1500):
            out += [f"### 前{top}", ""]
            for label, pairs_set in (("大跨", large), ("小跨", small)):
                total, chars, pairs = audit(records, top, pairs_set)
                out.append(f"- {label}主要键对：" + "、".join(
                    f"`{p}` {pct(v, total)}" for p, v in pairs.most_common(8)))
                out.append(f"- {label}主要字：" + "、".join(
                    f"{c} {pct(v, total)}" for c, v in chars.most_common(12)))
            out.append("")
        total, keys, third_total, third = heat(records, 1500)
        out += ["### 前1500按键热力", "",
                "- 全部简码：`" + "　".join(
                    f"{k.upper()} {pct(keys[k], total)}" for row in ROWS for k in row) + "`", "",
                "- 第三键：`" + "　".join(
                    f"{k.upper()} {pct(third[k], third_total)}" for row in ROWS for k in row) + "`", "",
                f"- 关注键：Z/X全部 {pct(keys['z'] + keys['x'], total)}；"
                f"F/H全部 {pct(keys['f'] + keys['h'], total)}；"
                f"Z/X第三键 {pct(third['z'] + third['x'], third_total)}；"
                f"F/H第三键 {pct(third['f'] + third['h'], third_total)}。", ""]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
