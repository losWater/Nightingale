#!/usr/bin/env python3
"""生成第二三键同手惩罚矩阵；用户指法B归右手。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


LEFT = set("qwertasdfgzxcv")
RIGHT = set("yuiophjklnmb")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists() or args.manifest.exists():
        raise ValueError("输出文件必须不存在")
    if LEFT & RIGHT or LEFT | RIGHT != set("abcdefghijklmnopqrstuvwxyz"):
        raise ValueError("左右手集合必须无交集并覆盖26字母")
    rows = []
    for first in "abcdefghijklmnopqrstuvwxyz":
        for second in "abcdefghijklmnopqrstuvwxyz":
            same = (first in LEFT and second in LEFT) or (first in RIGHT and second in RIGHT)
            rows.append(f"{first}{second}\t{1 if same else 0}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(rows) + "\n", encoding="utf-8")
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.manifest.write_text(json.dumps({
        "schema_version": 1,
        "purpose": "phonetic-shape hand separation",
        "left": "".join(sorted(LEFT)),
        "right": "".join(sorted(RIGHT)),
        "b_hand": "right",
        "same_hand_cost": 1,
        "cross_hand_cost": 0,
        "rows": len(rows),
        "output": str(args.output.resolve()),
        "sha256": digest,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
