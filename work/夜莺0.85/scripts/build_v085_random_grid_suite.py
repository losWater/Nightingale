#!/usr/bin/env python3
"""构建夜莺0.85随机开局的字词权重×三码奖励二维网格。"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
from pathlib import Path

import yaml

from build_v085_random_paired_suite import canonical, cross_objective, sha256, targets


PROFILES = [
    ("P1_w0p075_t70", 0.075, -70.0, 0.0),
    ("P2_w0p1_t70", 0.1, -70.0, 0.0),
    ("P3_w0p075_t90", 0.075, -90.0, 0.0),
    ("P4_w0p1_t90", 0.1, -90.0, 0.0),
    ("P5_w0p1_t90_sep2", 0.1, -90.0, 2.0),
]


def set_three_code_weight(config: dict, weight: float) -> None:
    tiers = config["optimization"]["objective"]["characters_short"]["tiers"]
    matches = [tier for tier in tiers if tier.get("top") == 6000]
    if len(matches) != 1:
        raise ValueError("必须恰有一个top=6000简码层")
    levels = matches[0].get("levels")
    level_matches = [level for level in levels if level.get("length") == 3]
    if len(level_matches) != 1:
        raise ValueError("top6000必须恰有一个length=3层")
    level_matches[0]["frequency"] = weight


def set_separation_weight(config: dict, weight: float) -> None:
    # 固定音码末键到首形键属于全码布局；挂在简码层会让一、二简退出统计。
    tiers = config["optimization"]["objective"]["characters_full"]["tiers"]
    matches = [tier for tier in tiers if tier.get("top") == 6000]
    if len(matches) != 1:
        raise ValueError("必须恰有一个top=6000简码层")
    matches[0]["phonetic_shape_transition_equivalence"] = weight


def normalized(config: dict, remove_mapping: bool = False) -> dict:
    value = copy.deepcopy(config)
    value.get("info", {}).pop("name", None)
    value.get("info", {}).pop("version", None)
    value["optimization"]["objective"].pop("character_word_collision", None)
    value["optimization"]["metaheuristic"]["parameters"].pop("steps", None)
    set_three_code_weight(value, 0.0)
    set_separation_weight(value, 0.0)
    if remove_mapping:
        value["form"].pop("mapping", None)
    return value


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-config", type=Path, required=True)
    ap.add_argument("--target-lexicon", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--starts", type=int, default=4)
    ap.add_argument("--seed-start", type=int, default=850101)
    ap.add_argument("--steps", type=int, default=100000)
    args = ap.parse_args()
    if args.output_dir.exists() or args.starts <= 0 or args.steps <= 0:
        raise ValueError("输出须不存在，starts和steps须为正")

    base = yaml.safe_load(args.base_config.read_text(encoding="utf-8"))
    space, mapping = base.get("generated_mapping_space"), base.get("form", {}).get("mapping")
    if not isinstance(space, dict) or not isinstance(mapping, dict) or set(space) != set(mapping):
        raise ValueError("基础映射决策空间不完整")
    base["optimization"]["objective"].pop("words_full", None)
    base["optimization"]["objective"].pop("character_word_collision", None)
    target_map = targets(args.target_lexicon)
    fixed = {name for name, choices in space.items() if len(choices) == 1}
    base_normalized = normalized(base, remove_mapping=True)

    args.output_dir.mkdir(parents=True, exist_ok=False)
    cards, layout_hashes, card_number = [], set(), 0
    for start in range(1, args.starts + 1):
        seed, rng = args.seed_start + start - 1, random.Random(args.seed_start + start - 1)
        candidate = {}
        for element, choices in space.items():
            if not choices:
                raise ValueError(f"空决策空间：{element}")
            candidate[element] = copy.deepcopy(rng.choice(choices)["value"] if len(choices) > 1 else choices[0]["value"])
        for element in fixed:
            if canonical(candidate[element]) != canonical(mapping[element]):
                raise AssertionError(f"固定元素漂移：{element}")
        for element in mapping:
            if element.startswith(("szm-", "mzm-")) and canonical(candidate[element]) != canonical(mapping[element]):
                raise AssertionError(f"音码飞键：{element}")
        layout_hash = hashlib.sha256(canonical(candidate).encode("utf-8")).hexdigest()
        if layout_hash in layout_hashes:
            raise ValueError("随机布局重复")
        layout_hashes.add(layout_hash)

        configs = []
        for profile, collision_weight, three_weight, separation_weight in PROFILES:
            card_number += 1
            cfg = copy.deepcopy(base)
            cfg["form"]["mapping"] = copy.deepcopy(candidate)
            cfg.setdefault("info", {})["name"] = f"夜莺0.85-S{start}_{profile}"
            cfg["info"]["version"] = "v0.85-random-grid-0004"
            cfg["optimization"]["objective"]["character_word_collision"] = cross_objective(collision_weight, target_map)
            set_three_code_weight(cfg, three_weight)
            set_separation_weight(cfg, separation_weight)
            cfg["optimization"]["metaheuristic"]["parameters"]["steps"] = args.steps
            if normalized(cfg, remove_mapping=True) != base_normalized:
                raise AssertionError("允许范围外配置漂移")
            label = f"S{start}_{profile}"
            directory = args.output_dir / label
            directory.mkdir()
            path = directory / "config.yaml"
            path.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False, width=10000), encoding="utf-8")
            cards.append({"card": card_number, "start": start, "seed": seed, "label": label,
                          "profile": profile, "collision_weight": collision_weight,
                          "three_code_weight": three_weight, "separation_weight": separation_weight,
                          "layout_sha256": layout_hash,
                          "directory": str(directory.resolve()), "config": str(path.resolve()),
                          "config_sha256": sha256(path), "status": "pending"})
            configs.append(cfg)
        signatures = {canonical(normalized(cfg)) for cfg in configs}
        if len(signatures) != 1:
            raise AssertionError(f"第{start}组除两项参数外并非同配置")

    manifest = {"schema_version": 1, "design": "v085-0004", "starts": args.starts,
                "profiles": [{"name": x[0], "collision_weight": x[1], "three_code_weight": x[2],
                              "separation_weight": x[3]} for x in PROFILES],
                "steps": args.steps, "seed_start": args.seed_start,
                "base_config": str(args.base_config.resolve()), "base_config_sha256": sha256(args.base_config),
                "target_lexicon": str(args.target_lexicon.resolve()), "target_lexicon_sha256": sha256(args.target_lexicon),
                "target_codes": len(target_map), "unique_layouts": len(layout_hashes), "cards": cards,
                "status": "built_pending_validation_and_run"}
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
