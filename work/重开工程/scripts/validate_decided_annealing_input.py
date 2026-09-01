#!/usr/bin/env python3
"""独立静态验收夜莺0.8退火频率、元素与配置。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import yaml


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unique_map(rows: list[dict[str, str]], value_column: str) -> dict[tuple[str, str], Decimal]:
    result: dict[tuple[str, str], Decimal] = {}
    for row in rows:
        pair = (row["汉字"], row["拼音"])
        if pair in result:
            raise ValueError(f"重复字音身份：{pair}")
        result[pair] = Decimal(row[value_column])
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--fused", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--elements", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--structures", type=Path, required=True)
    parser.add_argument("--special", type=Path, required=True)
    parser.add_argument("--residual", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    original_rows = read_tsv(args.original)
    fused_rows = read_tsv(args.fused)
    weight_rows = read_tsv(args.weights)
    structure_rows = read_tsv(args.structures)
    residual_rows = read_tsv(args.residual)
    original = unique_map(original_rows, "频率")
    fused = unique_map(fused_rows, "融合自然频率")
    weights = unique_map(weight_rows, "退火有效权重")
    identity_sets_equal = set(original) == set(fused) == set(weights)
    if not identity_sets_equal or len(original) != 8454:
        raise ValueError("三层字音身份集合不一致或不为8454")

    structures = {row["汉字"] for row in structure_rows}
    glyphs = {char for char, _ in original}
    if len(structures) != 8105 or glyphs != structures:
        raise ValueError("字音与8105结构字集不一致")

    element_rows = yaml.safe_load(args.elements.read_text(encoding="utf-8"))
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    if not isinstance(element_rows, list) or not isinstance(config, dict):
        raise ValueError("元素或配置YAML顶层结构错误")
    element_map: dict[tuple[str, str], Decimal] = {}
    mapping = config.get("form", {}).get("mapping", {})
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("配置缺少form.mapping")
    generated_space = config.get("generated_mapping_space")
    if not isinstance(generated_space, dict) or set(generated_space) != set(mapping):
        raise ValueError("generated_mapping_space未完整覆盖form.mapping")
    if any(not choices for choices in generated_space.values()):
        raise ValueError("generated_mapping_space含空决策列表")
    for row in element_rows:
        pair = (row["词"], row["拼音"])
        if pair in element_map:
            raise ValueError(f"元素表重复身份：{pair}")
        sequence = row["元素序列"]
        if isinstance(row.get("频率"), bool) or not isinstance(row.get("频率"), int) or row["频率"] < 0:
            raise ValueError(f"{pair}的Chai频率不是非负整数：{row.get('频率')!r}")
        if len(sequence) != 4:
            raise ValueError(f"{pair}元素序列长度不为4")
        unknown = [slot["element"] for slot in sequence if slot["element"] not in mapping]
        if unknown:
            raise ValueError(f"{pair}含配置未映射元素：{unknown}")
        element_map[pair] = Decimal(str(row["频率"]))
    if set(element_map) != set(weights) or any(element_map[pair] != weights[pair] for pair in weights):
        raise ValueError("元素身份／频率与有效权重表不一致")

    special_data = json.loads(args.special.read_text(encoding="utf-8"))
    expected_special = {
        (rule["character"], reading)
        for rule in special_data["rules"] for reading in rule["optimization"]
    }
    changed_by_special = {pair for pair in weights if weights[pair] != fused[pair]}
    if changed_by_special != expected_special:
        raise ValueError(f"特殊权重变化范围异常：{changed_by_special}")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    residual_total = sum(int(row["未分配频率"]) for row in residual_rows)
    if len(residual_rows) != manifest["residual_items"] or residual_total != manifest["residual_frequency"]:
        raise ValueError("残余未分配清单与生成清单不一致")

    changes = []
    for pair in original:
        before, after = original[pair], weights[pair]
        changes.append({
            "汉字": pair[0], "拼音": pair[1],
            "Chai原频率": str(before), "退火有效权重": str(after),
            "绝对变化": str(abs(after - before)),
            "变化方向": "增加" if after > before else "减少" if after < before else "不变",
        })
    changes.sort(key=lambda row: (-Decimal(row["绝对变化"]), row["汉字"], row["拼音"]))
    top_changes = changes[:100]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    changes_path = args.output_dir / "夜莺0.8退火输入_频率变化头部.tsv"
    with changes_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(top_changes[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(top_changes)

    report = {
        "status": "pass",
        "glyphs": len(glyphs), "reading_items": len(original), "element_rows": len(element_map),
        "identity_sets_equal": identity_sets_equal,
        "all_element_sequences_length_4": True,
        "all_elements_mapped": True,
        "element_frequencies_match_weights": True,
        "special_override_pairs": sorted([list(pair) for pair in changed_by_special]),
        "original_zero_items": sum(value == 0 for value in original.values()),
        "fused_zero_items": sum(value == 0 for value in fused.values()),
        "effective_zero_items": sum(value == 0 for value in weights.values()),
        "positive_to_zero_items": sum(original[pair] > 0 and weights[pair] == 0 for pair in original),
        "zero_to_positive_items": sum(original[pair] == 0 and weights[pair] > 0 for pair in original),
        "original_frequency_sum": str(sum(original.values())),
        "fused_frequency_sum": str(sum(fused.values())),
        "effective_weight_sum": str(sum(weights.values())),
        "residual_items": len(residual_rows), "residual_frequency": residual_total,
        "top_change_file_sha256": sha256(changes_path),
    }
    json_path = args.output_dir / "夜莺0.8退火输入_静态验收.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# 夜莺0.8退火输入静态验收", "",
        "- 状态：PASS",
        f"- 字／字音／元素：{report['glyphs']} / {report['reading_items']} / {report['element_rows']}",
        f"- 身份集合一致：{report['identity_sets_equal']}",
        f"- 元素序列全为4且均可映射：是",
        f"- 元素频率逐项匹配有效权重：是",
        f"- 零频（原始／融合／有效）：{report['original_zero_items']} / {report['fused_zero_items']} / {report['effective_zero_items']}",
        f"- 原正频→有效零频：{report['positive_to_zero_items']}；原零频→有效正频：{report['zero_to_positive_items']}",
        f"- 频率／权重总和（原始／融合／有效）：{report['original_frequency_sum']} / {report['fused_frequency_sum']} / {report['effective_weight_sum']}",
        f"- 特殊覆盖：{report['special_override_pairs']}",
        f"- 残余未分配：{report['residual_items']}项，{report['residual_frequency']}频率", "",
        "静态验收通过不代表退火指标已经优秀，只表示输入结构、身份、权重和裁决接线一致。", ""
    ]
    (args.output_dir / "夜莺0.8退火输入_静态验收.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
