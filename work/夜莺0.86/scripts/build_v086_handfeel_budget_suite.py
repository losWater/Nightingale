#!/usr/bin/env python3
"""从夜莺0.8.5冠军布局构建0.8.6手感换重码小规模配对实验。"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
from pathlib import Path

import yaml


PROFILES_BUDGET = [
    {"name": "A_v085", "three": -90.0, "large": 110.0, "small": 20.0, "separation": 0.25,
     "budget": 192},
    {"name": "B_plus10", "three": -80.0, "large": 125.0, "small": 30.0, "separation": 0.35,
     "budget": 202},
    {"name": "C_plus20", "three": -70.0, "large": 140.0, "small": 40.0, "separation": 0.50,
     "budget": 212},
]

PROFILES_SINGLE = [
    {"name": "A_v085", "three": -90.0, "large": 110.0, "small": 20.0,
     "separation": 0.25, "pair": 0.0, "budget": 580},
    {"name": "P_pair2", "three": -90.0, "large": 110.0, "small": 20.0,
     "separation": 0.25, "pair": 2.0, "budget": 580},
    {"name": "L_large140", "three": -90.0, "large": 140.0, "small": 20.0,
     "separation": 0.25, "pair": 0.0, "budget": 580},
    {"name": "S_small40", "three": -90.0, "large": 110.0, "small": 40.0,
     "separation": 0.25, "pair": 0.0, "budget": 580},
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tier(tiers: list[dict], top: int) -> dict:
    return next(item for item in tiers if item["top"] == top)


def apply_profile(config: dict, profile: dict, steps: int) -> None:
    objective = config["optimization"]["objective"]
    short = objective["characters_short"]["tiers"]
    full = objective["characters_full"]["tiers"]
    # 三码奖励只改前6000总目标；高频300/500/1674的保护保持0.8.5原值。
    tier(short, 6000)["levels"] = [{"length": 3, "frequency": profile["three"]}]
    # 大跨和小跨仍按既有指法向量的第2、3项入炉。
    for top in (300, 500, 1674):
        weights = tier(short, top)["weighted_fingering"]
        weights[1], weights[2] = profile["large"], profile["small"]
    tier(full, 6000)["phonetic_shape_transition_equivalence"] = profile["separation"]
    objective["characters_short"]["pair_equivalence"] = profile.get("pair", 0.0)
    config["optimization"]["metaheuristic"]["parameters"]["steps"] = steps


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-config", type=Path, required=True)
    parser.add_argument("--mapping-solution", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--chains", type=int, default=2)
    parser.add_argument("--steps", type=int, default=50000)
    parser.add_argument("--perturbations", type=int, default=12)
    parser.add_argument("--seed-start", type=int, default=860601)
    parser.add_argument("--profile-set", choices=("budget", "single"), default="budget")
    args = parser.parse_args()
    if args.output_dir.exists() or args.chains < 1 or args.steps < 1 or args.perturbations < 1:
        raise ValueError("输出目录必须不存在，chains/steps/perturbations必须为正")
    base = yaml.safe_load(args.base_config.read_text(encoding="utf-8"))
    solution = yaml.safe_load(args.mapping_solution.read_text(encoding="utf-8"))
    if not base.get("generated_mapping_space") or not base.get("form", {}).get("mapping"):
        raise ValueError("基础配置缺少布局或决策空间")
    solution_mapping = solution.get("form", {}).get("mapping")
    if not isinstance(solution_mapping, dict) or set(solution_mapping) != set(base["form"]["mapping"]):
        raise ValueError("结果解映射缺失或元素集合与基础配置不同")
    base["form"]["mapping"] = copy.deepcopy(solution_mapping)
    champion_mapping = copy.deepcopy(base["form"]["mapping"])
    space = base["generated_mapping_space"]
    movable = [name for name, choices in space.items()
               if len(choices) > 1 and not name.startswith(("szm-", "mzm-"))]
    if len(movable) < args.perturbations:
        raise ValueError("可移动字根不足")
    args.output_dir.mkdir(parents=True)
    profiles = PROFILES_SINGLE if args.profile_set == "single" else PROFILES_BUDGET
    cards = []
    for chain in range(1, args.chains + 1):
        rng = random.Random(args.seed_start + chain - 1)
        chain_mapping = copy.deepcopy(champion_mapping)
        changed = []
        for name in rng.sample(movable, args.perturbations):
            alternatives = [copy.deepcopy(item["value"]) for item in space[name]
                            if item["value"] != champion_mapping[name]]
            if alternatives:
                chain_mapping[name] = rng.choice(alternatives)
                changed.append(name)
        if len(changed) != args.perturbations:
            raise AssertionError("扰动数量不足")
        for profile in profiles:
            config = copy.deepcopy(base)
            config["form"]["mapping"] = copy.deepcopy(chain_mapping)
            apply_profile(config, profile, args.steps)
            if config["form"]["mapping"] != chain_mapping:
                raise AssertionError("配对起始布局发生漂移")
            label = f"R{chain}_{profile['name']}"
            config.setdefault("info", {})["name"] = f"夜莺0.8.6-{label}"
            config["info"]["version"] = "v0.86-handfeel-budget-smoke-0001"
            directory = args.output_dir / label
            directory.mkdir()
            path = directory / "config.yaml"
            path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
            cards.append({"card": len(cards) + 1, "chain": chain, "seed": args.seed_start + chain - 1,
                          "perturbed_elements": changed, "label": label, "profile": profile,
                          "directory": str(directory.resolve()), "config": str(path.resolve()),
                          "config_sha256": sha256(path), "status": "pending"})
    manifest = {"schema_version": 1, "design": "v086-handfeel-budget-smoke-0001",
                "base_config": str(args.base_config.resolve()), "base_config_sha256": sha256(args.base_config),
                "mapping_solution": str(args.mapping_solution.resolve()),
                "mapping_solution_sha256": sha256(args.mapping_solution),
                "chains": args.chains, "steps": args.steps, "perturbations": args.perturbations,
                "seed_start": args.seed_start, "profile_set": args.profile_set,
                "profiles": profiles, "cards": cards,
                "status": "built_pending_validation_and_run"}
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "cards": len(cards)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
