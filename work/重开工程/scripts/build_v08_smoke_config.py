#!/usr/bin/env python3
"""从已验收基础输入生成夜莺0.8端到端退火冒烟配置。"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import yaml


TOPS = (300, 500, 1500, 1674, 3527, 6000)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def zero_fingering() -> list[float]:
    return [0.0] * 8


def full_tier(top: int, front300_guard: float) -> dict:
    return {
        "top": top,
        "duplication": 0.0,
        "duplication_squared": 0.0,
        "effective_duplication": front300_guard if top == 300 else 0.0,
        "effective_duplication_squared": 0.0,
        "weighted_fingering": zero_fingering(),
        "phonetic_shape_transition_equivalence": 0.0,
    }


def short_tier(top: int, large_cross_weight: float, small_cross_weight: float,
               three_code_6000_weight: float) -> dict:
    tier = {
        "top": top,
        "duplication": 0.0,
        "duplication_squared": 0.0,
        "levels": [],
        "weighted_fingering": zero_fingering(),
        "phonetic_shape_transition_equivalence": 0.0,
    }
    if top in {300, 500, 1674, 3527}:
        tier["levels"] = [{"length": 3, "frequency": -15.0}]
    elif top == 6000:
        tier["levels"] = [{"length": 3, "frequency": three_code_6000_weight}]
    if top in {300, 500, 1674}:
        tier["weighted_fingering"] = [0.0, large_cross_weight, small_cross_weight, 0.0, 0.0, 0.0, 0.0, 0.0]
    return tier


def build(source: dict, front300_guard: float, large_cross_weight: float,
          small_cross_weight: float,
          three_code_6000_weight: float, steps: int) -> dict:
    result = copy.deepcopy(source)
    # 重开基础输入不继承旧简码所有权；退火实验必须显式启用Chai自然一/二/三码，
    # 否则简码目标为空并产生NaN。
    result["encoder"]["short_code"] = [{
        "length_equal": 1,
        "schemes": [
            {"prefix": 1, "count": 1},
            {"prefix": 2, "count": 1},
            {"prefix": 3, "count": 1},
        ],
    }]
    result["optimization"]["objective"] = {
        "characters_full": {
            "duplication": 0.0,
            "effective_duplication": 0.0,
            "pair_equivalence": 0.0,
            "phonetic_shape_transition_equivalence": 0.0,
            "fingering": zero_fingering(),
            "tiers": [full_tier(x, front300_guard) for x in TOPS],
        },
        "characters_short": {
            "duplication": 0.0,
            "pair_equivalence": 0.0,
            "phonetic_shape_transition_equivalence": 0.0,
            "fingering": zero_fingering(),
            "levels": [
                {"length": 1, "frequency": 0.0},
                {"length": 2, "frequency": 0.0},
                {"length": 3, "frequency": 0.0},
            ],
            "tiers": [short_tier(x, large_cross_weight, small_cross_weight,
                                  three_code_6000_weight) for x in TOPS],
        },
        "regularization_strength": 0.0,
    }
    result["optimization"]["metaheuristic"] = {
        "algorithm": "SimulatedAnnealing",
        "parameters": {
            "t_max": 4.455057485836668,
            "t_min": 0.0021753210380061855,
            "steps": steps,
        },
        "report_after": 0.99,
        "update_interval": 1000,
        "search_method": {
            "random_move": 0.90,
            "random_swap": 0.09,
            "random_full_key_swap": 0.01,
        },
    }
    if isinstance(result.get("info"), dict):
        result["info"]["name"] = "夜莺0.8-新输入退火冒烟-0038"
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--mapping-source", type=Path,
                        help="可选：只从另一完整/结果配置提取最终form.mapping")
    parser.add_argument("--front300-guard", type=float, default=4.0)
    parser.add_argument("--small-cross-weight", type=float, default=20.0)
    parser.add_argument("--large-cross-weight", type=float, default=100.0)
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--three-code-6000-weight", type=float, default=-70.0)
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        raise ValueError("输入与输出不得为同一路径")
    source_hash = sha256(args.source)
    if (args.front300_guard < 0 or args.large_cross_weight < 0
            or args.small_cross_weight < 0 or args.steps <= 0
            or args.three_code_6000_weight >= 0):
        raise ValueError("保护/小跨权重须非负，三码奖励须为负，步数须为正")
    result = build(yaml.safe_load(args.source.read_text(encoding="utf-8")),
                   args.front300_guard, args.large_cross_weight, args.small_cross_weight,
                   args.three_code_6000_weight, args.steps)
    mapping_source_hash = None
    if args.mapping_source is not None:
        mapping_source = yaml.safe_load(args.mapping_source.read_text(encoding="utf-8"))
        mapping = mapping_source.get("form", {}).get("mapping")
        if not isinstance(mapping, dict) or not mapping:
            raise ValueError("mapping-source没有非空form.mapping")
        result["form"]["mapping"] = copy.deepcopy(mapping)
        mapping_source_hash = sha256(args.mapping_source)
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(
        yaml.safe_dump(result, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    manifest = {
        "schema_version": 1,
        "design": "0038",
        "status": "config_generated_pending_native_validation_and_run",
        "source": str(args.source.resolve()),
        "source_sha256": source_hash,
        "output": str(args.output.resolve()),
        "output_sha256": sha256(args.output),
        "mapping_source": str(args.mapping_source.resolve()) if args.mapping_source else None,
        "mapping_source_sha256": mapping_source_hash,
        "metric_tops": list(TOPS),
        "threads": 2,
        "steps_per_thread": args.steps,
        "front300_effective_duplication_weight": args.front300_guard,
        "small_cross_weight": args.small_cross_weight,
        "large_cross_weight": args.large_cross_weight,
        "three_code_6000_weight": args.three_code_6000_weight,
        "short_code_policy": "natural_prefix1_prefix2_prefix3_count1_no_inherited_owners",
    }
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
