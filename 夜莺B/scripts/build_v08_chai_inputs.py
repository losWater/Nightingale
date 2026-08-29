# -*- coding: utf-8 -*-
"""从已审计的夜莺资产构建0.8 Chai基线配置与单字编码对象。"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

import yaml


FINGERING_ZERO = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
TIERS = (300, 500, 1674, 3527)
PERFORMANCE_TOP = 6000


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read_tier(path: Path, expected: int, label: str) -> list[str]:
    chars = [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines()
             if line.strip()]
    if len(chars) != expected or len(set(chars)) != expected:
        raise ValueError(f"{label}必须恰有{expected}个不重复字，实际{len(chars)}/{len(set(chars))}")
    if any(len(char) != 1 for char in chars):
        raise ValueError(f"{label}混入非单字")
    return chars


def build_elements(source: list[dict], core: list[str], common: list[str]) -> tuple[list[dict], dict]:
    if not isinstance(source, list) or not source:
        raise ValueError("elements必须是非空列表")
    result = []
    removed = Counter()
    one_codes = 0
    for index, original in enumerate(source, 1):
        if not isinstance(original, dict) or "词" not in original:
            raise ValueError(f"elements第{index}项格式错误")
        word = str(original["词"])
        if len(word) != 1:
            raise ValueError(f"0.8单字资产混入非单字：第{index}项 {word!r}")
        item = copy.deepcopy(original)
        level = item.get("简码长度")
        if level == 1:
            one_codes += 1
        elif level is not None:
            removed[f"removed_level_{level}"] += 1
            item.pop("简码长度", None)
        item.pop("排序序号", None)
        result.append(item)
    if one_codes != 26:
        raise ValueError(f"固定一简必须恰为26条，实际{one_codes}")
    words = [str(item["词"]) for item in result]
    if len(set(words)) != len(words):
        raise ValueError("elements存在重复单字")
    word_set, core_set, common_set = set(words), set(core), set(common)
    if not core_set <= common_set:
        raise ValueError("1674核心层不是3527常用层的子集")
    missing = common_set - word_set
    if missing:
        raise ValueError(f"3527常用层有字不在elements：{sorted(missing)[:10]}")
    by_word = {str(item["词"]): item for item in result}
    # 两份名单的行序就是各自审计后的内部顺序；核心先排，随后排常用层新增字。
    ordered_words = core + [char for char in common if char not in core_set]
    rest = sorted((item for item in result if str(item["词"]) not in common_set),
                  key=lambda item: -int(item.get("频率", 0)))
    reordered = [by_word[char] for char in ordered_words] + rest
    for order, item in enumerate(reordered):
        item["排序序号"] = order
    if {str(item["词"]) for item in reordered[:len(core)]} != core_set:
        raise AssertionError(f"前{len(core)}未精确覆盖核心层")
    if {str(item["词"]) for item in reordered[:len(common)]} != common_set:
        raise AssertionError(f"前{len(common)}未精确覆盖常用层")
    return reordered, {"rows": len(reordered), "one_codes": one_codes,
                       "core_tier": len(core), "common_tier": len(common),
                       "explicit_sort_order": len(reordered), **dict(removed)}


def measurement_objective() -> dict:
    full_tiers = [{
        "top": top,
        "duplication": 0.0,
        "duplication_squared": 0.0,
        "effective_duplication": 0.0,
        "effective_duplication_squared": 0.0,
        "weighted_fingering": list(FINGERING_ZERO),
        "phonetic_shape_transition_equivalence": 0.0,
    } for top in TIERS]
    full_tiers.append({
        "top": PERFORMANCE_TOP,
        "duplication": 0.0,
        "duplication_squared": 0.0,
        "effective_duplication": 0.0,
        "effective_duplication_squared": 0.0,
    })
    short_tiers = [{
        "top": top,
        "duplication": 0.0,
        "duplication_squared": 0.0,
        "levels": [{"length": 3, "frequency": 0.0}],
        "weighted_fingering": list(FINGERING_ZERO),
        "phonetic_shape_transition_equivalence": 0.0,
    } for top in TIERS]
    short_tiers.append({
        "top": PERFORMANCE_TOP,
        "duplication": 0.0,
        "duplication_squared": 0.0,
        "levels": [{"length": 3, "frequency": 0.0}],
    })
    return {
        "characters_full": {
            "duplication": 0.0,
            "effective_duplication": 0.0,
            "pair_equivalence": 0.0,
            "phonetic_shape_transition_equivalence": 0.0,
            "fingering": list(FINGERING_ZERO),
            "tiers": full_tiers,
        },
        "characters_short": {
            "duplication": 0.0,
            "pair_equivalence": 0.0,
            "phonetic_shape_transition_equivalence": 0.0,
            "fingering": list(FINGERING_ZERO),
            "levels": [
                {"length": 1, "frequency": 0.0},
                {"length": 2, "frequency": 0.0},
                {"length": 3, "frequency": 0.0},
            ],
            "tiers": short_tiers,
        },
        "regularization_strength": 0.0,
    }


def build_config(source: dict) -> dict:
    config = copy.deepcopy(source)
    config["version"] = "0.8"
    if isinstance(config.get("info"), dict):
        config["info"]["name"] = "夜莺0.8基线测量"
    short_code = config["encoder"].setdefault("short_code", [])
    one_char_rule = {
        "length_equal": 1,
        "schemes": [
            {"prefix": 2, "count": 1},
            {"prefix": 3, "count": 1},
        ],
    }
    replaced = False
    for index, rule in enumerate(short_code):
        if rule.get("length_equal") == 1:
            short_code[index] = one_char_rule
            replaced = True
    if not replaced:
        short_code.insert(0, one_char_rule)
    config["optimization"]["objective"] = measurement_objective()
    meta = config["optimization"].get("metaheuristic")
    if meta is not None:
        meta["parameters"]["steps"] = 1_000
        meta["update_interval"] = 1_000
    return config


def build(source_config: Path, source_elements: Path, output_config: Path,
          output_elements: Path, manifest_path: Path,
          core_chars: Path, common_chars: Path) -> dict:
    resolved = [path.resolve() for path in (
        source_config, source_elements, output_config, output_elements, manifest_path,
        core_chars, common_chars
    )]
    if len(set(resolved)) != len(resolved):
        raise ValueError("输入与输出路径必须彼此不同，禁止原地覆盖")
    source_cfg = yaml.safe_load(source_config.read_text(encoding="utf-8"))
    source_rows = yaml.safe_load(source_elements.read_text(encoding="utf-8"))
    core = read_tier(core_chars, 1674, "核心层")
    common = read_tier(common_chars, 3527, "常用层")
    rows, counts = build_elements(source_rows, core, common)
    config = build_config(source_cfg)
    output_config.parent.mkdir(parents=True, exist_ok=True)
    output_elements.parent.mkdir(parents=True, exist_ok=True)
    output_config.write_text(yaml.safe_dump(
        config, allow_unicode=True, sort_keys=False, width=10_000
    ), encoding="utf-8")
    output_elements.write_text(yaml.safe_dump(
        rows, allow_unicode=True, sort_keys=False, width=10_000
    ), encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "purpose": "nightingale-v08-baseline-measurement",
        "source": {
            "config": {"path": str(source_config.resolve()), "sha256": sha256(source_config)},
            "elements": {"path": str(source_elements.resolve()), "sha256": sha256(source_elements)},
            "core_chars": {"path": str(core_chars.resolve()), "sha256": sha256(core_chars)},
            "common_chars": {"path": str(common_chars.resolve()), "sha256": sha256(common_chars)},
        },
        "output": {
            "config": {"path": str(output_config.resolve()), "sha256": sha256(output_config)},
            "elements": {"path": str(output_elements.resolve()), "sha256": sha256(output_elements)},
        },
        "transform": {
            **counts,
            "character_tiers": list(TIERS),
            "performance_top": PERFORMANCE_TOP,
            "objective_weights": "all-zero-measurement-only",
            "discarded_objectives": ["character_word_collision", "auxiliary_two_char"],
            "single_character_short_code": "fixed-one-code_then_prefix2-count1_then_prefix3-count1",
        },
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(
        manifest, ensure_ascii=False, indent=2
    ) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-config", type=Path, required=True)
    parser.add_argument("--source-elements", type=Path, required=True)
    parser.add_argument("--output-config", type=Path, required=True)
    parser.add_argument("--output-elements", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--core-chars", type=Path, required=True)
    parser.add_argument("--common-chars", type=Path, required=True)
    args = parser.parse_args()
    manifest = build(args.source_config, args.source_elements, args.output_config,
                     args.output_elements, args.manifest, args.core_chars, args.common_chars)
    print(json.dumps(manifest["transform"], ensure_ascii=False))


if __name__ == "__main__":
    main()
