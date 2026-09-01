#!/usr/bin/env python3
"""以Chai恢复整字总频，用当前分读音证据比例生成融合频率预览。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def largest_remainder(total: int, weights: dict[str, int]) -> dict[str, int]:
    weight_sum = sum(weights.values())
    if weight_sum <= 0:
        raise ValueError("比例权重总和必须为正")
    exact = {key: Decimal(total) * Decimal(value) / Decimal(weight_sum) for key, value in weights.items()}
    result = {key: int(value) for key, value in exact.items()}
    remainder = total - sum(result.values())
    order = sorted(exact, key=lambda key: (-(exact[key] - result[key]), key))
    for key in order[:remainder]:
        result[key] += 1
    if sum(result.values()) != total:
        raise AssertionError("融合分配不守恒")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chai", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    chai_rows = read_tsv(args.chai)
    evidence_rows = read_tsv(args.evidence)
    chai_by_char: dict[str, list[dict[str, str]]] = defaultdict(list)
    evidence_by_pair: dict[tuple[str, str], int] = {}
    for row in chai_rows:
        chai_by_char[row["汉字"]].append(row)
    for row in evidence_rows:
        evidence_by_pair[(row["汉字"], row["拼音"])] = int(row["退火候选自然频率"])
    chai_pairs = {(row["汉字"], row["拼音"]) for row in chai_rows}
    if len(chai_rows) != 8454 or len(chai_by_char) != 8105 or set(evidence_by_pair) != chai_pairs:
        raise ValueError("Chai与证据表字音身份不一致")

    output: list[dict[str, str | int]] = []
    anomalies: list[dict[str, str | int]] = []
    conserved_chars = 0
    duplicated_total_chars = 0
    for char, rows in chai_by_char.items():
        chai_frequencies = {row["拼音"]: int(row["频率"]) for row in rows}
        positives = [value for value in chai_frequencies.values() if value > 0]
        if len(positives) >= 2 and len(set(positives)) == 1:
            glyph_total = positives[0]
            total_basis = "相等正频视为整字频复制，只取一份"
            duplicated_total_chars += 1
        else:
            glyph_total = sum(positives)
            total_basis = "Chai正频求和" if positives else "Chai全零"

        evidence = {reading: evidence_by_pair[(char, reading)] for reading in chai_frequencies}
        if len(rows) == 1:
            allocation = {next(iter(chai_frequencies)): glyph_total}
            allocation_basis = "单读音直接取得整字总频"
            conserved = True
        elif sum(evidence.values()) > 0:
            allocation = largest_remainder(glyph_total, evidence)
            allocation_basis = "按当前明确分读音证据比例守恒拆分"
            conserved = True
        else:
            allocation = chai_frequencies
            allocation_basis = "无正频比例证据，暂保留Chai原值"
            conserved = sum(allocation.values()) == glyph_total
            anomalies.append({
                "汉字": char,
                "Chai整字总频": glyph_total,
                "Chai原分读音频率": ";".join(f"{key}:{chai_frequencies[key]}" for key in sorted(chai_frequencies)),
                "当前比例证据": ";".join(f"{key}:{evidence[key]}" for key in sorted(evidence)),
                "兜底结果": ";".join(f"{key}:{allocation[key]}" for key in sorted(allocation)),
                "是否守恒": "是" if conserved else "否",
                "原因": allocation_basis,
            })
        if conserved:
            conserved_chars += 1

        for row in rows:
            reading = row["拼音"]
            output.append({
                "汉字": char, "拼音": reading,
                "Chai原字音频率": chai_frequencies[reading],
                "Chai整字总频": glyph_total,
                "当前比例证据": evidence[reading],
                "融合自然频率": allocation[reading],
                "整字总频口径": total_basis,
                "分配口径": allocation_basis,
            })

    output.sort(key=lambda row: (-int(row["融合自然频率"]), str(row["汉字"]), str(row["拼音"])))
    anomalies.sort(key=lambda row: (-int(row["Chai整字总频"]), str(row["汉字"])))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "Chai总频_分读音比例融合预览.tsv"
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(output)
    anomaly_path = args.output_dir / "Chai总频_分读音比例融合异常.tsv"
    with anomaly_path.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["汉字", "Chai整字总频", "Chai原分读音频率", "当前比例证据", "兜底结果", "是否守恒", "原因"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(anomalies)

    original_zero = sum(int(row["频率"]) == 0 for row in chai_rows)
    fused_zero = sum(int(row["融合自然频率"]) == 0 for row in output)
    positive_to_zero = sum(int(row["Chai原字音频率"]) > 0 and int(row["融合自然频率"]) == 0 for row in output)
    zero_to_positive = sum(int(row["Chai原字音频率"]) == 0 and int(row["融合自然频率"]) > 0 for row in output)
    report = {
        "glyphs": len(chai_by_char), "reading_items": len(output),
        "duplicated_total_pattern_characters": duplicated_total_chars,
        "conserved_characters": conserved_chars,
        "fallback_anomaly_characters": len(anomalies),
        "fallback_nonconserved_characters": sum(row["是否守恒"] == "否" for row in anomalies),
        "original_zero_reading_items": original_zero,
        "fused_zero_reading_items": fused_zero,
        "positive_to_zero_items": positive_to_zero,
        "zero_to_positive_items": zero_to_positive,
        "original_frequency_sum": sum(int(row["频率"]) for row in chai_rows),
        "fused_frequency_sum": sum(int(row["融合自然频率"]) for row in output),
        "preview_sha256": sha256(output_path), "anomaly_sha256": sha256(anomaly_path),
    }
    (args.output_dir / "Chai总频_分读音比例融合报告.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = ["# Chai总频与分读音比例融合报告", ""] + [f"- {key}: {value}" for key, value in report.items()] + ["", "本轮只生成融合预览，未覆盖退火输入。", ""]
    (args.output_dir / "Chai总频_分读音比例融合报告.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
