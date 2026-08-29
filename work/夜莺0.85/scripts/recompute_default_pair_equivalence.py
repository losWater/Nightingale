#!/usr/bin/env python3
"""用默认键对矩阵从实际简码重新计算频率加权组合当量。"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_equivalence(path: Path) -> dict[str, float]:
    result = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) != 2 or len(fields[0]) != 2:
            raise ValueError(f"当量表第{number}行异常")
        result[fields[0]] = float(fields[1])
    return result


def load_codes(path: Path) -> list[tuple[str, str]]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        fields = line.split("\t")
        if len(fields) < 5 or not fields[3]:
            raise ValueError(f"码表第{number}行异常")
        rows.append((fields[0], fields[3]))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--elements", type=Path, required=True)
    ap.add_argument("--equivalence", type=Path, required=True)
    ap.add_argument("--candidate", action="append", required=True, help="名称=code.txt")
    ap.add_argument("--output-json", type=Path, required=True)
    ap.add_argument("--output-md", type=Path, required=True)
    args = ap.parse_args()
    elements = yaml.safe_load(args.elements.read_text(encoding="utf-8"))
    matrix = load_equivalence(args.equivalence)
    results = {}
    inputs = {str(args.elements.resolve()): sha256(args.elements),
              str(args.equivalence.resolve()): sha256(args.equivalence)}
    for spec in args.candidate:
        name, separator, raw_path = spec.partition("=")
        if not separator or not name:
            raise ValueError("candidate必须为名称=code.txt")
        path = Path(raw_path)
        rows = load_codes(path)
        if len(rows) != len(elements):
            raise ValueError(f"{name}码表与元素表行数不一致")
        total, denominator = 0.0, 0
        for index, (item, (word, code)) in enumerate(zip(elements, rows), 1):
            if str(item.get("词")) != word:
                raise ValueError(f"{name}第{index}行身份错位")
            frequency = int(item.get("频率", 0))
            for left, right in zip(code, code[1:]):
                pair = left + right
                if pair not in matrix:
                    raise ValueError(f"默认当量表缺键对：{pair}")
                total += matrix[pair] * frequency
                denominator += frequency
        if denominator <= 0:
            raise ValueError(f"{name}没有加权键对")
        results[name] = {"identities": len(rows), "weighted_pairs": denominator,
                         "pair_equivalence": total / denominator,
                         "code": str(path.resolve()), "code_sha256": sha256(path)}
        inputs[str(path.resolve())] = sha256(path)
    report = {"schema_version": 1, "metric": "default_short_pair_equivalence",
              "inputs": inputs, "candidates": results}
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 默认简码组合当量复测", "", "|候选|身份|加权键对|默认简码当量|", "|---|---:|---:|---:|"]
    lines.extend(f"|{name}|{row['identities']}|{row['weighted_pairs']}|{row['pair_equivalence']:.12f}|"
                 for name, row in results.items())
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
