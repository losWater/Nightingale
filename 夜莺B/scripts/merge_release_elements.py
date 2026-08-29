# -*- coding: utf-8 -*-
"""保留定稿元素资产的频率/排序，仅合入最新字形序列。"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def asset_key(item):
    sound = tuple(
        (str(slot["element"]), int(slot.get("index", 0)))
        for slot in item["元素序列"][:2]
    )
    return str(item["词"]), sound


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline", type=Path)
    ap.add_argument("fresh", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()

    baseline = yaml.safe_load(args.baseline.read_text(encoding="utf-8"))
    fresh = yaml.safe_load(args.fresh.read_text(encoding="utf-8"))
    fresh_by_key = {asset_key(item): item for item in fresh}
    if len(fresh_by_key) != len(fresh):
        raise ValueError("最新元素资产存在重复的字/读音键")

    changed = 0
    for item in baseline:
        key = asset_key(item)
        source = fresh_by_key.pop(key, None)
        if source is None:
            raise ValueError(f"最新元素资产缺少：{key}")
        new_sequence = item["元素序列"][:2] + source["元素序列"][2:]
        if new_sequence != item["元素序列"]:
            changed += 1
            item["元素序列"] = new_sequence
    if fresh_by_key:
        raise ValueError(f"最新元素资产多出 {len(fresh_by_key)} 项")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        yaml.safe_dump(baseline, allow_unicode=True, sort_keys=False, width=10000),
        encoding="utf-8",
    )
    print(f"elements={len(baseline)} form_changed={changed} output={args.output}")


if __name__ == "__main__":
    main()
