#!/usr/bin/env python3
"""把既有快符按显式候选位加入搜狗自定义短语表。"""
from __future__ import annotations

import argparse
from collections import OrderedDict
from pathlib import Path


def parse_table(path: Path) -> tuple[list[str], OrderedDict[str, dict[int, str]]]:
    headers: list[str] = []
    slots: OrderedDict[str, dict[int, str]] = OrderedDict()
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line:
            continue
        if line.startswith(";"):
            headers.append(line)
            continue
        left, value = line.split("=", 1)
        code, position_text = left.rsplit(",", 1)
        position = int(position_text)
        bucket = slots.setdefault(code, {})
        if position in bucket:
            raise ValueError(f"源表第{line_no}行位次重复：{code},{position}")
        bucket[position] = value
    return headers, slots


def parse_quick(path: Path) -> list[tuple[str, int, str]]:
    result = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        left, value = line.split("=", 1)
        code, position_text = left.rsplit(",", 1)
        result.append((code, int(position_text), value))
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--quick", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise ValueError("输出文件已存在，拒绝覆盖")

    headers, slots = parse_table(args.source)
    before = {(code, pos, value) for code, bucket in slots.items() for pos, value in bucket.items()}
    quick = parse_quick(args.quick)
    for code, position, value in quick:
        bucket = slots.setdefault(code, {})
        if position in bucket:
            raise ValueError(f"快符位置与原表冲突：{code},{position}={value}，原值={bucket[position]}")
        bucket[position] = value

    after_original = {(code, pos, value) for code, bucket in slots.items()
                      for pos, value in bucket.items() if (code, pos, value) in before}
    if after_original != before:
        raise ValueError("加入快符后原单字码或候选序号发生变化")

    lines = [headers[0] + "＋既有快符",
             "; 含源单字表的全部已登记裁决及symbo.txt快符；不含词表或简词", ""]
    for code, bucket in slots.items():
        positions = sorted(bucket)
        if positions != list(range(1, max(positions) + 1)):
            raise ValueError(f"码位{code}存在候选序号空洞：{positions}")
        for position in positions:
            lines.append(f"{code},{position}={bucket[position]}")
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"单字{len(before)}条，快符{len(quick)}条，合计{len(before)+len(quick)}条：{args.output}")


if __name__ == "__main__":
    main()
