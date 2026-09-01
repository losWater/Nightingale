#!/usr/bin/env python3
"""把新生成的扩展字全码排到所有既有候选之后。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-codes", type=Path, required=True)
    parser.add_argument("--combined", type=Path, required=True)
    parser.add_argument("--short-words", type=Path, required=True)
    parser.add_argument("--quick", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for name in ("full_codes", "combined", "short_words", "quick", "output"):
        setattr(args, name, getattr(args, name).resolve())

    occupied: dict[str, set[int]] = defaultdict(set)
    by_code: dict[str, int] = defaultdict(int)
    for raw in args.combined.read_text(encoding="utf-8-sig").splitlines():
        _text, code = raw.split("\t")
        by_code[code] += 1
        occupied[code].add(by_code[code])
    with args.short_words.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            occupied[row["简码"]].add(int(row["候选位"]))
    for raw in args.quick.read_text(encoding="utf-8-sig").splitlines():
        left, _ = raw.split("=", 1)
        code, rank = left.rsplit(",", 1)
        occupied[code].add(int(rank))

    with args.full_codes.open(encoding="utf-8-sig", newline="") as stream:
        source = list(csv.DictReader(stream, delimiter="\t"))
    rows = []
    violations = []
    for row in source:
        char, code = row["汉字"], row["全码"]
        before = max(occupied[code], default=0)
        rank = before + 1
        occupied[code].add(rank)
        if rank <= before:
            violations.append({"汉字": char, "全码": code, "候选位": rank, "此前末位": before})
        rows.append({"字": char, "码": code, "候选位": rank})
    if violations:
        raise ValueError(f"扩展字末位规则失效：{violations[:5]}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["字", "码", "候选位"], delimiter="\t", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    report = {
        "rows": len(rows),
        "unique_characters": len({row["字"] for row in rows}),
        "codes": len({row["码"] for row in rows}),
        "rank_min": min(int(row["候选位"]) for row in rows),
        "rank_max": max(int(row["候选位"]) for row in rows),
        "rows_after_existing_candidates": len(rows),
        "violations": 0,
        "inputs": {path.name: sha256(path) for path in [args.full_codes, args.combined, args.short_words, args.quick]},
        "output_sha256": sha256(args.output),
    }
    args.output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
