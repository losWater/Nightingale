#!/usr/bin/env python3
"""物化退火有效权重，并由当前8105结构生成8454条四元素输入。"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

import yaml

import audit_manual_split_propagation as common


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def chai_frequency(value: Decimal) -> int:
    """Chai 的元素频率是 u64；拒绝把小数或负数静默写入输入。"""
    if value < 0 or value != value.to_integral_value():
        raise ValueError(f"Chai频率必须为非负整数：{value}")
    return int(value)


def apply_algebra(rules: list[dict], value: str) -> str:
    result = value
    for rule in rules:
        if rule.get("type") != "xform":
            raise ValueError(f"不支持的algebra规则：{rule}")
        replacement = re.sub(r"\$(\d+)", r"\\g<\1>", str(rule["to"]))
        result = re.sub(str(rule["from"]), replacement, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frequencies", type=Path, required=True)
    parser.add_argument("--special-evidence", type=Path, required=True)
    parser.add_argument("--special-weights", type=Path, required=True)
    parser.add_argument("--residual", type=Path, required=True)
    parser.add_argument("--structures", type=Path, required=True)
    parser.add_argument("--output-frequency", type=Path, required=True)
    parser.add_argument("--output-elements", type=Path, required=True)
    parser.add_argument("--output-config", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    frequency_rows = read_tsv(args.frequencies)
    special_evidence_rows = read_tsv(args.special_evidence)
    structure_rows = read_tsv(args.structures)
    residual_rows = read_tsv(args.residual)
    if len(frequency_rows) != 8454 or len(structure_rows) != 8105:
        raise ValueError(f"输入数量异常：字音{len(frequency_rows)}，结构{len(structure_rows)}")
    structures = {row["汉字"]: row for row in structure_rows}
    if len(structures) != 8105:
        raise ValueError("8105结构表含重复汉字")

    rules_data = json.loads(args.special_weights.read_text(encoding="utf-8"))
    overrides: dict[tuple[str, str], tuple[Decimal, str]] = {}
    for rule in rules_data["rules"]:
        char = rule["character"]
        expected_stage = rule["evidence_guard"]["stage_frequency_by_reading"]
        actual_stage = {
            row["拼音"]: int(row["退火候选自然频率"])
            for row in special_evidence_rows if row["汉字"] == char
        }
        if actual_stage != expected_stage:
            raise ValueError(f"{char} 自然频率快照变化：{actual_stage} != {expected_stage}")
        for reading, config in rule["optimization"].items():
            if config["participates_in_competition"]:
                effective = Decimal(config["expected_effective_weight"])
            else:
                effective = Decimal(config["effective_weight"])
            overrides[(char, reading)] = (effective, config["reason"])

    weight_rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in frequency_rows:
        pair = (row["汉字"], row["拼音"])
        if pair in seen:
            raise ValueError(f"重复字音身份：{pair}")
        seen.add(pair)
        natural = Decimal(row["融合自然频率"])
        if pair in overrides:
            effective, reason = overrides[pair]
            source = "特殊优化权重覆盖"
        else:
            effective, reason = natural, "默认等于自然频率候选"
            source = "自然频率"
        weight_rows.append({
            "汉字": pair[0], "拼音": pair[1],
            "退火候选自然频率": decimal_text(natural),
            "退火有效权重": decimal_text(effective),
            "权重来源": source, "原因": reason,
        })
    if set(overrides) - seen:
        raise ValueError(f"特殊权重指向不存在的字音：{set(overrides) - seen}")
    changed = [row for row in weight_rows if row["退火候选自然频率"] != row["退火有效权重"]]
    if { (row["汉字"], row["拼音"]) for row in changed } != set(overrides):
        raise ValueError("特殊权重变化范围与裁决资产不一致")

    args.output_frequency.parent.mkdir(parents=True, exist_ok=True)
    with args.output_frequency.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(weight_rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(weight_rows)

    roots = yaml.safe_load(common.ROOTS_PATH.read_text(encoding="utf-8"))
    baseline = yaml.safe_load(common.BASELINE_PATH.read_text(encoding="utf-8"))
    by_name, _ = common.repertoire_maps(baseline)
    algebra = baseline.get("algebra") or {}
    if not algebra.get("szm") or not algebra.get("mzm"):
        raise ValueError("基础配置缺少szm/mzm algebra")

    config = yaml.safe_load(yaml.safe_dump(baseline, allow_unicode=True, sort_keys=False))
    # libchai 的 repertoire.gb2312 使用 u8；旧基线YAML中的 false 必须规范为0。
    for repertoire_item in config.get("data", {}).get("repertoire", {}).values():
        if isinstance(repertoire_item.get("gb2312"), bool):
            repertoire_item["gb2312"] = int(repertoire_item["gb2312"])
    old_mapping = config["form"]["mapping"]
    mapping = {str(key): value for key, value in old_mapping.items() if str(key).startswith(("szm-", "mzm-"))}
    mains: list[str] = []
    for root in roots["roots"]:
        element = common.resolve(root, by_name)
        if element not in mains:
            mains.append(element)
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    for index, element in enumerate(mains):
        mapping[element] = alphabet[index % len(alphabet)]
    for host_name, attached in roots["roots"].items():
        host = common.resolve(host_name, by_name)
        for name in attached or []:
            child = common.resolve(name, by_name)
            if child != host:
                mapping[child] = {"element": host}
    anchored_elements: set[str] = set()
    for host_name, anchored in (roots.get("anchors") or {}).items():
        host = common.resolve(host_name, by_name)
        for name in anchored or []:
            child = common.resolve(name, by_name)
            mapping[child] = {"element": host}
            anchored_elements.add(child)
    mapping["6"] = {"element": "5"}
    config["form"]["mapping"] = mapping
    config["form"]["alphabet"] = alphabet
    config["form"]["mapping_space"] = {}
    # WebChai 图形界面的“生成”步骤会物化此字段；直接调用 libchai 时必须由输入
    # 构建器显式生成。音码、附属根与锨定根固定；只有未锨定的主根可在26键间移动。
    main_set = set(mains)
    generated_mapping_space = {}
    for element, current in mapping.items():
        values = list(alphabet) if element in main_set and element not in anchored_elements else [copy.deepcopy(current)]
        generated_mapping_space[element] = [
            {"value": value, "score": 0.0} for value in values
        ]
    config["generated_mapping_space"] = generated_mapping_space
    config["info"] = {
        "name": "夜莺0.8退火基础配置",
        "author": "nightingale",
        "version": "v0.8-frequency-decisions",
        "description": "当前8105结构、8454字音身份及正式频率裁决；无简码和附加码。",
    }

    items: list[dict] = []
    for row in weight_rows:
        char, pinyin = row["汉字"], row["拼音"]
        source = pinyin + "5"
        initial = "szm-" + apply_algebra(algebra["szm"], source)
        final = "mzm-" + apply_algebra(algebra["mzm"], source)
        structure = structures.get(char)
        if structure is None:
            raise ValueError(f"字音不属于当前8105：{char}")
        head = common.resolve(structure["编码首根"], by_name)
        tail = common.resolve(structure["编码末根"], by_name)
        sequence = [initial, final, head, tail]
        unknown = [element for element in sequence if element not in mapping]
        if unknown:
            raise ValueError(f"{char}/{pinyin}含未映射元素：{unknown}")
        items.append({
            "词": char, "拼音": pinyin,
            "元素序列": [{"element": element, "index": 0} for element in sequence],
            "频率": chai_frequency(Decimal(row["退火有效权重"])),
        })
    if len(items) != 8454 or {item["词"] for item in items} != set(structures):
        raise ValueError("退火元素覆盖异常")
    if any(len(item["元素序列"]) != 4 for item in items):
        raise ValueError("退火元素序列长度异常")

    args.output_elements.parent.mkdir(parents=True, exist_ok=True)
    args.output_elements.write_text(yaml.safe_dump(items, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
    args.output_config.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
    roundtrip = yaml.safe_load(args.output_elements.read_text(encoding="utf-8"))
    if len(roundtrip) != 8454 or {(item["词"], item["拼音"]) for item in roundtrip} != seen:
        raise ValueError("退火元素写回校验失败")

    residual_total = sum(int(row["未分配频率"]) for row in residual_rows)
    manifest = {
        "status": "v0.8_annealing_input_pending_algorithm_run",
        "glyphs": 8105, "reading_items": 8454, "element_rows": len(items),
        "special_weight_overrides": len(overrides),
        "residual_items": len(residual_rows), "residual_frequency": residual_total,
        "zero_effective_weight_rows": sum(Decimal(row["退火有效权重"]) == 0 for row in weight_rows),
        "inputs": {str(path): sha256(path) for path in [args.frequencies, args.special_evidence, args.special_weights, args.residual, args.structures, common.ROOTS_PATH, common.NAME_ALIASES_PATH, common.BASELINE_PATH]},
        "outputs": {str(path): sha256(path) for path in [args.output_frequency, args.output_elements, args.output_config]},
    }
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
