#!/usr/bin/env python3
"""校验并物化特殊退火优化权重；不改写自然频率或退火输入。"""

from __future__ import annotations

import argparse
import csv
import json
from decimal import Decimal
from pathlib import Path


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def stage_frequency(row: dict[str, str]) -> int:
    """兼容设计0029阶段表和后续人工定案阶段表。"""
    for column in ("退火候选自然频率", "人工定案后阶段频率", "封闭集合阶段合计频率"):
        if column in row:
            return int(row[column])
    raise ValueError("阶段表缺少可识别的合计频率列")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    rules = json.loads(args.rules.read_text(encoding="utf-8"))
    stage_rows = read_tsv(args.stage)
    audit_rows = read_tsv(args.audit)
    output_rows: list[dict[str, str]] = []
    report_lines = ["# 特殊优化权重裁决验证", ""]

    for rule in rules["rules"]:
        char = rule["character"]
        guard = rule["evidence_guard"]
        expected_stage = guard["stage_frequency_by_reading"]
        actual_stage = {
            row["拼音"]: stage_frequency(row)
            for row in stage_rows
            if row["汉字"] == char
        }
        if actual_stage != expected_stage:
            raise ValueError(f"{char} 阶段频率变化：期望 {expected_stage}，实际 {actual_stage}")

        matching_audit = [row for row in audit_rows if row["汉字"] == char]
        if len(matching_audit) != 1:
            raise ValueError(f"{char} 定案审计行数应为 1，实际 {len(matching_audit)}")
        unallocated = int(matching_audit[0]["SUBTLEX单字总频"])
        if unallocated != guard["unallocated_single_character_frequency"]:
            raise ValueError(f"{char} 未分配单字频率变化：{unallocated}")

        glyph_total = unallocated + sum(actual_stage.values())
        if glyph_total != guard["glyph_total_frequency"]:
            raise ValueError(f"{char} 整字总频变化：{glyph_total}")

        report_lines.extend([
            f"## {char}", "",
            f"- 已分读音阶段频率：{actual_stage}",
            f"- 尚未分读音单字频率：{unallocated}",
            f"- 当前可审计整字总频：{glyph_total}", ""
        ])
        for reading in rule["closed_readings"]:
            config = rule["optimization"][reading]
            if config["participates_in_competition"]:
                effective = (
                    Decimal(glyph_total)
                    * Decimal(config["multiplier_numerator"])
                    / Decimal(config["multiplier_denominator"])
                )
                expected = Decimal(config["expected_effective_weight"])
                if effective != expected:
                    raise ValueError(f"{char}/{reading} 有效权重变化：{effective}")
            else:
                effective = Decimal(config["effective_weight"])

            output_rows.append({
                "汉字": char,
                "拼音": reading,
                "音码": rule["input_keys"][reading],
                "自然频率处理": "证据表保持不变",
                "参与退火竞争": "是" if config["participates_in_competition"] else "否",
                "退火有效权重": decimal_text(effective),
                "整字总频口径": str(glyph_total),
                "原因": config["reason"],
            })
            report_lines.append(
                f"- `{reading} / {rule['input_keys'][reading]}`："
                f"{'参与' if config['participates_in_competition'] else '不参与'}竞争；"
                f"有效权重 `{decimal_text(effective)}`。"
            )
        report_lines.extend(["", "自然频率证据未被改写；本结果仅属于退火优化权重层。", ""])

    args.output_dir.mkdir(parents=True, exist_ok=True)
    tsv_path = args.output_dir / "特殊优化权重裁决_验证.tsv"
    with tsv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(output_rows)
    (args.output_dir / "特殊优化权重裁决_验证报告.md").write_text(
        "\n".join(report_lines), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
