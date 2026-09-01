#!/usr/bin/env python3
"""由字词在前的正式主表生成编码在前的等价镜像表。"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    output: list[str] = []
    for line_number, raw in enumerate(args.source.read_text(encoding="utf-8-sig").splitlines(), 1):
        parts = raw.split("\t")
        if len(parts) != 2:
            raise ValueError(f"{args.source}:{line_number}: 应为‘字词<Tab>编码’")
        text, code = parts
        if not text or not code.isascii() or not code.isalpha() or not code.islower():
            raise ValueError(f"{args.source}:{line_number}: 非法条目")
        output.append(f"{code}\t{text}")
    args.output.write_bytes(("\n".join(output) + "\n").encode("utf-8"))
    print(f"码前镜像表={len(output)}条")


if __name__ == "__main__":
    main()
